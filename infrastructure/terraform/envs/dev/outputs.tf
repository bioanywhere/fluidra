output "chat_api_url" {
  description = "Public URL of the chat-api Cloud Run service."
  value       = module.chat_api.uri
}

output "lb_ip" {
  description = "External Application Load Balancer IP for chat-api (if enabled)."
  value       = try(module.loadbalancer[0].ip, null)
}

output "registry_path" {
  description = "Artifact Registry path to push images to."
  value       = module.registry.repository_path
}

output "db_connection_name" {
  value = module.sql.connection_name
}

output "wif_provider" {
  description = "Set as the WIF_PROVIDER GitHub secret for the deploy workflow."
  value       = module.wif.provider_name
}

output "deployer_sa_email" {
  description = "Set as the DEPLOY_SA GitHub secret for the deploy workflow."
  value       = module.wif.deployer_sa_email
}
