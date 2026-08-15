# Terraform configuration for ANNEX infrastructure
# Run with: terraform init && terraform plan && terraform apply

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  backend "gcs" {
    bucket = "annex-terraform-state"
    prefix = "infrastructure"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# =========================================================================
# VARIABLES
# =========================================================================
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
  default     = "staging"
}

variable "db_password" {
  description = "Cloud SQL root password"
  type        = string
  sensitive   = true
}

# =========================================================================
# RANDOM RESOURCES
# =========================================================================
resource "random_password" "db_password" {
  length  = 32
  special = false
}

# =========================================================================
# ARTIFACT REGISTRY
# =========================================================================
resource "google_artifact_registry_repository" "annex" {
  location      = var.region
  repository_id = "annex"
  description   = "ANNEX Docker images"
  format        = "DOCKER"
}

# =========================================================================
# CLOUD SQL (PostgreSQL)
# =========================================================================
resource "google_sql_database_instance" "annex_db" {
  name             = "annex-db-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region
  deletion_protection = var.environment == "production"

  settings {
    tier              = var.environment == "production" ? "db-custom-2-4096" : "db-f1-micro"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = var.environment == "production" ? 100 : 10
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled            = true
      start_time         = "03:00"
      point_in_time_recovery = var.environment == "production"
    }

    maintenance_window {
      day  = 7
      hour = 4
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
}

resource "google_sql_database" "annex" {
  name     = "annex"
  instance = google_sql_database_instance.annex_db.name
}

# =========================================================================
# REDIS (Memorystore)
# =========================================================================
resource "google_redis_instance" "annex_redis" {
  name           = "annex-redis-${var.environment}"
  region         = var.region
  tier           = "BASIC"
  memory_size_gb = var.environment == "production" ? 2 : 1
  redis_version  = "REDIS_7_0"

  authorized_network = google_compute_network.vpc.id

  redis_configs = {
    "maxmemory-policy" = "allkeys-lru"
  }
}

# =========================================================================
# VPC NETWORK
# =========================================================================
resource "google_compute_network" "vpc" {
  name                    = "annex-vpc-${var.environment}"
  auto_create_subnetworks = false
  deletion_protection     = var.environment == "production"
}

resource "google_compute_subnetwork" "private" {
  name          = "annex-private-${var.environment}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "cloudrun" {
  name          = "annex-cloudrun-${var.environment}"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  purpose       = "PRIVATE_SERVICE_CONNECT"
  role          = "ACTIVE"
}

# VPC Connector for Cloud Run to access private resources
resource "google_vpc_access_connector" "cloudrun" {
  name           = "annex-connector-${var.environment}"
  region         = var.region
  network        = google_compute_network.vpc.id
  subnet         = google_compute_subnetwork.private.id
  min_instances  = 2
  max_instances  = 10
  machine_type   = "e2-micro"
}

# =========================================================================
# SECRET MANAGER
# =========================================================================
locals {
  secrets = [
    "DATABASE_URL",
    "REDIS_URL",
    "FIREBASE_PROJECT_ID",
    "FIREBASE_SERVICE_ACCOUNT",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "SENTRY_DSN",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each = toset(local.secrets)
  secret_id = lower(each.key)
  replication {
    automatic = true
  }
  labels = {
    environment = var.environment
    project     = "annex"
  }
}

# Secret versions (to be populated via CI/CD)
resource "google_secret_manager_secret_version" "secrets" {
  for_each = toset(local.secrets)
  secret   = google_secret_manager_secret.secrets[each.key].id
  secret_data = var.environment == "production" ? "SET_VIA_CI_PROD" : "SET_VIA_CI_STAGING"
}

# =========================================================================
# CLOUD RUN SERVICE
# =========================================================================
resource "google_cloud_run_v2_service" "backend" {
  name     = "annex-backend-${var.environment}"
  location = var.region
  deletion_protection = var.environment == "production"

  template {
    service_account = google_service_account.cloudrun.email
    timeout         = "300s"
    max_instance_request_concurrency = 80

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/annex/backend:latest"
      ports {
        container_port = 8000
      }
      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
        startup_cpu_boost = true
      }
      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }
      # Secrets
      dynamic "env" {
        for_each = local.secrets
        content {
          name = each.value
          value_source {
            secret_key_ref {
              secret = google_secret_manager_secret.secrets[each.value].secret_id
              version = "latest"
            }
          }
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = var.environment == "production" ? 20 : 10
    }

    vpc_access {
      network_interfaces {
        network = google_compute_network.vpc.name
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# =========================================================================
# CLOUD RUN JOB (Migrations)
# =========================================================================
resource "google_cloud_run_v2_job" "migration" {
  name     = "annex-migration-${var.environment}"
  location = var.region

  template {
    service_account = google_service_account.cloudrun.email
    timeout         = "300s"
    max_retries     = 3

    template {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/annex/backend-migration:latest"
        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
        env {
          name  = "APP_ENV"
          value = var.environment
        }
        dynamic "env" {
          for_each = local.secrets
          content {
            name = each.value
            value_source {
              secret_key_ref {
                secret = google_secret_manager_secret.secrets[each.value].secret_id
                version = "latest"
              }
            }
          }
        }
      }
      vpc_access {
        network_interfaces {
          network = google_compute_network.vpc.name
        }
      }
    }
  }
}

# =========================================================================
# SERVICE ACCOUNTS & IAM
# =========================================================================
resource "google_service_account" "cloudrun" {
  account_id   = "annex-cloudrun-${var.environment}"
  display_name = "ANNEX Cloud Run Service Account"
  description  = "Service account for ANNEX Cloud Run services"
}

# Grant Secret Manager access
resource "google_secret_manager_secret_iam_member" "cloudrun_access" {
  for_each = toset(local.secrets)
  secret_id = google_secret_manager_secret.secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Grant Cloud SQL Client
resource "google_project_iam_member" "cloudsql_client" {
  role   = "roles/cloudsql.client"
  member = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Grant Redis access
resource "google_project_iam_member" "redis_access" {
  role   = "roles/redis.editor"
  member = "serviceAccount:${google_service_account.cloudrun.email}"
}

# =========================================================================
# MONITORING & ALERTING
# =========================================================================
resource "google_monitoring_notification_channel" "slack" {
  count = var.environment == "production" ? 1 : 0
  display_name = "ANNEX Slack Alerts"
  type         = "slack"
  labels = {
    channel_name = "#annex-alerts"
    auth_token   = var.slack_webhook_url
  }
}

resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "ANNEX High Error Rate"
  combiner     = "OR"
  conditions {
    display_name = "Error rate > 1%"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"annex-backend-${var.environment}\" AND metric.type=\"run.googleapis.com/request_count\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields    = ["resource.labels.revision_name"]
      }
    }
  }
  notification_channels = var.environment == "production" ? [google_monitoring_notification_channel.slack[0].id] : []
  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "ANNEX High Latency"
  combiner     = "OR"
  conditions {
    display_name = "P99 latency > 2s"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"annex-backend-${var.environment}\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_99"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields    = ["resource.labels.revision_name"]
      }
    }
  }
  notification_channels = var.environment == "production" ? [google_monitoring_notification_channel.slack[0].id] : []
}

# =========================================================================
# OUTPUTS
# =========================================================================
output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
  description = "Cloud Run backend URL"
}

output "artifact_registry_repo" {
  value = google_artifact_registry_repository.annex.id
  description = "Artifact Registry repository"
}

output "cloudsql_connection_name" {
  value = google_sql_database_instance.annex_db.connection_name
  description = "Cloud SQL connection name"
  sensitive   = true
}

output "redis_host" {
  value = google_redis_instance.annex_redis.host
  description = "Redis host"
}

output "vpc_connector" {
  value = google_vpc_access_connector.cloudrun.id
  description = "VPC Access Connector"
}