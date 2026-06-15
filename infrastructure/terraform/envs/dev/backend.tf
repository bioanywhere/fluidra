# Remote state in GCS (blueprint §3). Create the bucket once, out-of-band:
#   gsutil mb -l europe-west1 gs://<your-tf-state-bucket>
#   gsutil versioning set on gs://<your-tf-state-bucket>
# Then either fill in the bucket below or pass it at init time:
#   terraform init -backend-config="bucket=<your-tf-state-bucket>"
terraform {
  backend "gcs" {
    # bucket = "fluidra-pool-asst-tfstate"   # set here or via -backend-config
    prefix = "dev"
  }
}
