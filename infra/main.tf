data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Latest Amazon Linux 2023 AMI (x86_64).
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# CloudFront's origin-facing IP ranges — used to lock the API security group so
# the EC2 origin is reachable only via CloudFront, not the open internet.
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

# Default VPC + one public subnet for the demo instance.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
