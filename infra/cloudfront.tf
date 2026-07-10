locals {
  s3_origin_id  = "s3-dashboard"
  api_origin_id = "ec2-api"
  # API paths proxied to the EC2 origin (everything else is served from S3).
  api_path_patterns = ["/health", "/runs", "/runs/*", "/budget", "/scenarios"]

  # AWS-managed policy IDs.
  caching_optimized_id = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
  caching_disabled_id  = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # CachingDisabled
  all_viewer_orp_id    = "216adef6-5c7f-47e4-b989-5492eb8f4c0f" # AllViewer origin-request policy
}

resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${var.project}-s3-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  comment             = "${var.project} dashboard + API proxy"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  # S3 origin (the static dashboard).
  origin {
    domain_name              = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_id                = local.s3_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  # EC2 origin (the FastAPI service) over HTTP — CloudFront terminates HTTPS for
  # the browser, so there is no mixed-content and no cross-origin (same-origin).
  origin {
    domain_name = aws_eip.api.public_dns
    origin_id   = local.api_origin_id
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default: serve the dashboard from S3.
  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = local.caching_optimized_id
    compress               = true
  }

  # API paths: proxy to the EC2 origin, no caching, forward everything, allow POST.
  dynamic "ordered_cache_behavior" {
    for_each = local.api_path_patterns
    content {
      path_pattern             = ordered_cache_behavior.value
      target_origin_id         = local.api_origin_id
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods           = ["GET", "HEAD"]
      cache_policy_id          = local.caching_disabled_id
      origin_request_policy_id = local.all_viewer_orp_id
      compress                 = true
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
