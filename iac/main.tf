# data to get the resources already created

data "aws_ecr_repository" "lambda-ecr-repo" {
  name = "example-lambda"
}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }

  tags = {
    Type = "public"
  }
}

locals {
  image_tag = "latest"
  image_uri = strcontains(data.aws_ecr_repository.lambda-ecr-repo.repository_url, ":") ? "${data.aws_ecr_repository.lambda-ecr-repo.repository_url}" : "${data.aws_ecr_repository.lambda-ecr-repo.repository_url}:${local.image_tag}"
}

resource "aws_security_group" "lambda_sg" {
  name        = "lambda_security_group"
  description = "Security group for Lambda in VPC"
  vpc_id      = data.aws_vpc.selected.id

  # Allow Lambda to connect to RDS
#   egress {
#     from_port       = 5432
#     to_port         = 5432
#     protocol        = "tcp"
#     security_groups = [aws_security_group.rds_sg.id]  # Reference RDS SG
#   }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}


resource "aws_lambda_function" "lambda_function" {
    function_name = "${var.aws_lambda_function}"
    timeout       = 5 # seconds
    image_uri = local.image_uri
    package_type  = "Image"
    role = aws_iam_role.lambda_role.arn

    vpc_config {
        subnet_ids         = data.aws_subnets.public.ids  # Use private subnets
        security_group_ids = [aws_security_group.lambda_sg.id]    # Attach security group
  }
}

resource "aws_iam_role" "lambda_role" {
    name = "lambda_execution_role"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
        {
            Effect = "Allow"
            Principal = {
            Service = "lambda.amazonaws.com"
            }
            Action = "sts:AssumeRole"
        }
        ]
    })
    }

resource "aws_iam_policy_attachment" "lambda_basic_execution" {
    name       = "lambda_basic_execution_attachment"
    roles      = [aws_iam_role.lambda_role.name]
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    }

# Full RDS Access
resource "aws_iam_policy_attachment" "lambda_rds_access" {
    name       = "lambda_rds_access_attachment"
    roles      = [aws_iam_role.lambda_role.name]
    policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess" 
    }

resource "aws_iam_policy" "lambda_ecr_policy" {
    name        = "LambdaPolicy"
    description = "Policy for Lambda to pull images from ECR and create lambda in VPC"

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect   = "Allow"
                Action   = [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability"
                ]
                Resource = "${data.aws_ecr_repository.lambda-ecr-repo.arn}"
            },
            {
                Effect = "Allow"
                Action = "ecr:GetAuthorizationToken"
                Resource = "*"
            },
            {
                Effect = "Allow"
                Action = [
                    "ec2:CreateNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface"
                ],
                Resource = "*"
            }
        ]
    })
    }

resource "aws_iam_policy_attachment" "lambda_ecr_attachment" {
    name       = "lambda_ecr_attachment"
    roles      = [aws_iam_role.lambda_role.name]
    policy_arn = aws_iam_policy.lambda_ecr_policy.arn
    }


# Create API Gateway (HTTP API, NOT REST API)
resource "aws_apigatewayv2_api" "http_api" {
  name          = "http-api"
  protocol_type = "HTTP"
}

# Create API Gateway Route
resource "aws_apigatewayv2_route" "http_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /search"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Create API Gateway Integration with Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.lambda_function.invoke_arn
}

# Deploy API Gateway Stage
resource "aws_apigatewayv2_stage" "http_stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# Allow API Gateway to Invoke Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
}


# Create a Security Group for RDS
resource "aws_security_group" "rds_sg" {
    name        = "rds-security-group"
    description = "Allow inbound traffic to RDS"
    vpc_id      = data.aws_vpc.selected.id

    # Allow incoming connections on PostgreSQL port from Lambda SG
    ingress {
        from_port       = 5432
        to_port         = 5432
        protocol        = "tcp"
        security_groups = [aws_security_group.lambda_sg.id]  # Reference Lambda SG
    }
    ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.ip_address]
    }

    # Allow all outbound traffic
    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}

# Create an RDS Subnet Group
resource "aws_db_subnet_group" "rds_subnet_group" {
    name       = "rds-subnet-group"
    subnet_ids = data.aws_subnets.public.ids 

    tags = {
        Name = "RDS Subnet Group"
  }
}

# Create RDS PostgreSQL Instance
resource "aws_db_instance" "rds_postgres" {
    allocated_storage      = 20
    storage_type           = "gp3"
    engine                = "postgres"
    engine_version        = "17.2" 
    instance_class        = "db.t3.micro"
    identifier            = "my-postgres-db"
    username              = var.db_username
    password              = var.db_password
    #   parameter_group_name  = "default.postgres15"
    publicly_accessible   = true # Set to false for private RDS
    skip_final_snapshot   = true
    multi_az = false
    vpc_security_group_ids = [aws_security_group.rds_sg.id]
    db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name

    tags = {
        Name = "MyPostgresDB"
  }
}


# Output RDS Endpoint
output "rds_endpoint" {
    value = aws_db_instance.rds_postgres.endpoint
}

# Output API Gateway URL
output "http_api_url" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "lambda_function_arn" {
  value = aws_lambda_function.lambda_function.arn
}
