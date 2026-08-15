terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "lambda_function_arn" {
  description = "ARN of the lambda_trigger_pipeline Lambda function"
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the lambda_trigger_pipeline Lambda function"
  type        = string
}

resource "aws_cloudwatch_event_rule" "weekly_job_market_pipeline" {
  name                = "job-market-intel-agent-weekly"
  description         = "Triggers the weekly tech job market intelligence pipeline"
  schedule_expression = "cron(0 8 ? * MON *)" # every Monday at 08:00 UTC
}

resource "aws_cloudwatch_event_target" "trigger_pipeline_lambda" {
  rule      = aws_cloudwatch_event_rule.weekly_job_market_pipeline.name
  target_id = "trigger-pipeline-lambda"
  arn       = var.lambda_function_arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_job_market_pipeline.arn
}
