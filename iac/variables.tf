variable "aws_lambda_function" {
    default = "test_lambda"
    type = string  
}

variable "vpc_id" {
    type = string
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "ip_address" {
  type      = string
  sensitive = true
}
