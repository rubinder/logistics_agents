# --- IAM: instance role (read the Anthropic key from SSM + Session Manager) ---
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  name               = "${var.project}-api"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "read_key" {
  statement {
    sid     = "ReadAnthropicKey"
    actions = ["ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.anthropic_key_ssm_name}"
    ]
  }
  statement {
    sid     = "DecryptSsm"
    actions = ["kms:Decrypt"]
    # Restrict to the SSM service so this can only decrypt SSM SecureStrings.
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "read_key" {
  name   = "read-anthropic-key"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.read_key.json
}

resource "aws_iam_instance_profile" "api" {
  name = "${var.project}-api"
  role = aws_iam_role.api.name
}

# --- Networking: security group locked to CloudFront's origin IPs (no SSH) ---
resource "aws_security_group" "api" {
  name        = "${var.project}-api"
  description = "API reachable only from CloudFront; egress open"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "HTTP from CloudFront origin-facing ranges"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Compute: the demo instance ---
resource "aws_instance" "api" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.api.id]
  iam_instance_profile   = aws_iam_instance_profile.api.name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region        = var.region
    ssm_key_name  = var.anthropic_key_ssm_name
    repo_url      = var.repo_url
    repo_branch   = var.repo_branch
    budget_cap    = var.budget_cap_usd
    per_ip_daily  = var.per_ip_daily
    global_daily  = var.global_daily
    trigger_model = var.trigger_model
  })

  # Re-run user_data when its inputs change.
  user_data_replace_on_change = true

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-api" }
}

resource "aws_eip" "api" {
  domain   = "vpc"
  instance = aws_instance.api.id
  tags     = { Name = "${var.project}-api" }
}
