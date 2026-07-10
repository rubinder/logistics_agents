output "dashboard_url" {
  description = "Public HTTPS URL of the dashboard (and API proxy)."
  value       = "https://${aws_cloudfront_distribution.this.domain_name}"
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.this.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.this.id
}

output "s3_bucket" {
  description = "Bucket to sync the built dashboard into."
  value       = aws_s3_bucket.dashboard.id
}

output "api_origin_dns" {
  description = "EC2 origin CloudFront proxies API paths to."
  value       = aws_eip.api.public_dns
}

output "instance_id" {
  value = aws_instance.api.id
}
