variable "project" {
  type    = string
  default = "logistics-agents"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "repo_url" {
  type    = string
  default = "https://github.com/rubinder/logistics_agents.git"
}

variable "repo_branch" {
  description = "Branch the EC2 clones and runs (the M8 branch carries the whole stack)."
  type        = string
  default     = "milestone-8-aws-deploy"
}

variable "anthropic_key_ssm_name" {
  description = "SSM SecureString parameter holding the Anthropic API key. Created out-of-band so the secret never enters Terraform state."
  type        = string
  default     = "/logistics-agents/anthropic-api-key"
}

# Conservative public-demo spend guards (env-driven in the API).
variable "budget_cap_usd" {
  type    = number
  default = 5
}

variable "per_ip_daily" {
  type    = number
  default = 5
}

variable "global_daily" {
  type    = number
  default = 30
}

variable "trigger_model" {
  type    = string
  default = "claude-haiku-4-5"
}
