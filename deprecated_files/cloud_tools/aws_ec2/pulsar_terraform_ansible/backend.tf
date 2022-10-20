terraform {
  backend "s3" {
    bucket = "icecube-terraform-states"
    key    = "skymap/pulsar.tfstate"
    region = "us-east-2"
  }
}
