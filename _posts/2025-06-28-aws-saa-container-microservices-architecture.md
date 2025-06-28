---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 컨테이너 오케스트레이션과 마이크로서비스 아키텍처"
date: 2025-06-28
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 컨테이너 오케스트레이션과 마이크로서비스 아키텍처

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 컨테이너 기반 마이크로서비스 아키텍처 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 ECS, EKS, Fargate를 활용한 현대적인 애플리케이션 설계와 운영 전략을 다룹니다.

## 📝 실전 문제

**문제**: 한 핀테크 스타트업이 모놀리식 애플리케이션을 마이크로서비스로 전환하려고 합니다. 현재 상황과 요구사항은 다음과 같습니다:

**현재 상황:**
- Java Spring Boot 기반 모놀리식 애플리케이션
- MySQL 데이터베이스와 Redis 캐시 사용
- 일일 활성 사용자 100만명, 피크 시간 트래픽 급증
- 개발팀 50명, 6개 스쿼드로 구성

**요구사항:**
- **마이크로서비스 분리**: 사용자, 결제, 알림, 거래 등 도메인별 분리
- **컨테이너 기반**: Docker 컨테이너로 배포 및 운영
- **자동 확장**: 트래픽에 따른 자동 스케일링
- **무중단 배포**: Blue/Green 또는 Rolling 배포
- **서비스 간 통신**: API Gateway, 메시징, 서비스 디스커버리
- **모니터링**: 분산 추적, 로그 집계, 메트릭 수집
- **보안**: 컨테이너 보안, 네트워크 격리, 암호화

가장 적절한 컨테이너 기반 마이크로서비스 아키텍처는?

**A)** EC2 + Docker Swarm + ELB + CloudWatch

**B)** ECS Fargate + ALB + API Gateway + X-Ray + CloudWatch + Secrets Manager

**C)** EKS + EC2 Node Groups + Classic Load Balancer + Lambda

**D)** Elastic Beanstalk + Multi-container Docker + RDS + ElastiCache

## 🎯 정답 및 해설

### 정답: B

**ECS Fargate + ALB + API Gateway + X-Ray + CloudWatch + Secrets Manager**

### 상세 분석

#### 1. 요구사항별 서비스 매핑

| 요구사항 | AWS 서비스 | 설명 |
|----------|------------|------|
| **컨테이너 오케스트레이션** | **ECS Fargate** | 서버리스 컨테이너, 관리 오버헤드 최소화 |
| **로드 밸런싱** | **ALB** | Layer 7 라우팅, 컨테이너 기반 서비스 지원 |
| **API 관리** | **API Gateway** | 마이크로서비스 API 통합, 인증, 제한 |
| **서비스 디스커버리** | **ECS Service Discovery** | 자동 DNS 기반 서비스 검색 |
| **분산 추적** | **X-Ray** | 마이크로서비스 간 요청 추적 |
| **모니터링/로깅** | **CloudWatch** | 통합 로그 및 메트릭 수집 |
| **보안 관리** | **Secrets Manager** | 암호, API 키 안전한 관리 |

#### 2. 마이크로서비스 아키텍처 설계 원칙

```
API Gateway → ALB → ECS Services (Fargate)
├── User Service (사용자 관리)
├── Payment Service (결제 처리)
├── Notification Service (알림)
├── Transaction Service (거래)
├── Auth Service (인증)
└── Analytics Service (분석)
```

## 🚀 상세 아키텍처 설계

### 1. ECS Fargate 클러스터 구성

#### ECS 클러스터 생성
```json
{
  "ECSClusterConfiguration": {
    "ClusterName": "fintech-microservices-cluster",
    "CapacityProviders": ["FARGATE", "FARGATE_SPOT"],
    "DefaultCapacityProviderStrategy": [
      {
        "CapacityProvider": "FARGATE",
        "Weight": 3,
        "Base": 2
      },
      {
        "CapacityProvider": "FARGATE_SPOT",
        "Weight": 1
      }
    ],
    "ClusterSettings": [
      {
        "Name": "containerInsights",
        "Value": "enabled"
      }
    ],
    "Tags": [
      {
        "Key": "Environment",
        "Value": "production"
      },
      {
        "Key": "Project",
        "Value": "fintech-microservices"
      }
    ]
  }
}
```

#### 마이크로서비스별 태스크 정의
```json
{
  "UserServiceTaskDefinition": {
    "Family": "user-service",
    "NetworkMode": "awsvpc",
    "RequiresCompatibilities": ["FARGATE"],
    "Cpu": "1024",
    "Memory": "2048",
    "ExecutionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
    "TaskRoleArn": "arn:aws:iam::account:role/userServiceTaskRole",
    "ContainerDefinitions": [
      {
        "Name": "user-service",
        "Image": "fintech/user-service:latest",
        "Essential": true,
        "PortMappings": [
          {
            "ContainerPort": 8080,
            "Protocol": "tcp"
          }
        ],
        "Environment": [
          {
            "Name": "SPRING_PROFILES_ACTIVE",
            "Value": "production"
          },
          {
            "Name": "DATABASE_URL",
            "Value": "jdbc:mysql://user-db.cluster-xyz.ap-northeast-2.rds.amazonaws.com:3306/userdb"
          }
        ],
        "Secrets": [
          {
            "Name": "DATABASE_PASSWORD",
            "ValueFrom": "arn:aws:secretsmanager:ap-northeast-2:account:secret:user-db-password"
          },
          {
            "Name": "JWT_SECRET",
            "ValueFrom": "arn:aws:secretsmanager:ap-northeast-2:account:secret:jwt-secret"
          }
        ],
        "LogConfiguration": {
          "LogDriver": "awslogs",
          "Options": {
            "awslogs-group": "/ecs/user-service",
            "awslogs-region": "ap-northeast-2",
            "awslogs-stream-prefix": "ecs"
          }
        },
        "HealthCheck": {
          "Command": [
            "CMD-SHELL",
            "curl -f http://localhost:8080/health || exit 1"
          ],
          "Interval": 30,
          "Timeout": 5,
          "Retries": 3,
          "StartPeriod": 60
        }
      }
    ]
  }
}
```

### 2. ECS 서비스 및 오토스케일링

#### ECS 서비스 구성
```python
import boto3
import json

def create_ecs_service():
    """ECS 서비스 생성 및 오토스케일링 설정"""
    
    ecs_client = boto3.client('ecs')
    autoscaling_client = boto3.client('application-autoscaling')
    
    # 사용자 서비스 생성
    user_service = ecs_client.create_service(
        cluster='fintech-microservices-cluster',
        serviceName='user-service',
        taskDefinition='user-service:latest',
        desiredCount=3,
        launchType='FARGATE',
        platformVersion='LATEST',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [
                    'subnet-private-1a',
                    'subnet-private-1c'
                ],
                'securityGroups': [
                    'sg-user-service'
                ],
                'assignPublicIp': 'DISABLED'
            }
        },
        loadBalancers=[
            {
                'targetGroupArn': 'arn:aws:elasticloadbalancing:ap-northeast-2:account:targetgroup/user-service-tg',
                'containerName': 'user-service',
                'containerPort': 8080
            }
        ],
        serviceRegistries=[
            {
                'registryArn': 'arn:aws:servicediscovery:ap-northeast-2:account:service/srv-user-service'
            }
        ],
        deploymentConfiguration={
            'maximumPercent': 200,
            'minimumHealthyPercent': 50,
            'deploymentCircuitBreaker': {
                'enable': True,
                'rollback': True
            }
        },
        enableExecuteCommand=True
    )
    
    # Auto Scaling 대상 등록
    autoscaling_client.register_scalable_target(
        ServiceNamespace='ecs',
        ResourceId=f'service/fintech-microservices-cluster/user-service',
        ScalableDimension='ecs:service:DesiredCount',
        MinCapacity=2,
        MaxCapacity=50,
        RoleARN='arn:aws:iam::account:role/application-autoscaling-ecs-service'
    )
    
    # CPU 기반 스케일링 정책
    cpu_scaling_policy = autoscaling_client.put_scaling_policy(
        PolicyName='user-service-cpu-scaling',
        ServiceNamespace='ecs',
        ResourceId='service/fintech-microservices-cluster/user-service',
        ScalableDimension='ecs:service:DesiredCount',
        PolicyType='TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration={
            'TargetValue': 70.0,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ECSServiceAverageCPUUtilization'
            },
            'ScaleOutCooldown': 300,
            'ScaleInCooldown': 300
        }
    )
    
    # 메모리 기반 스케일링 정책
    memory_scaling_policy = autoscaling_client.put_scaling_policy(
        PolicyName='user-service-memory-scaling',
        ServiceNamespace='ecs',
        ResourceId='service/fintech-microservices-cluster/user-service',
        ScalableDimension='ecs:service:DesiredCount',
        PolicyType='TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration={
            'TargetValue': 80.0,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ECSServiceAverageMemoryUtilization'
            },
            'ScaleOutCooldown': 300,
            'ScaleInCooldown': 600
        }
    )
    
    return user_service['service']['serviceArn']

# ECS 서비스 생성
service_arn = create_ecs_service()
print(f"User service created: {service_arn}")
```

### 3. API Gateway 통합

#### API Gateway 구성
```json
{
  "APIGatewayConfiguration": {
    "RestApiName": "fintech-microservices-api",
    "Description": "Fintech microservices API gateway",
    "EndpointConfiguration": {
      "Types": ["REGIONAL"]
    },
    "Resources": [
      {
        "PathPart": "users",
        "HttpMethods": [
          {
            "HttpMethod": "GET",
            "Integration": {
              "Type": "HTTP_PROXY",
              "IntegrationHttpMethod": "GET",
              "Uri": "http://user-service.fintech.local:8080/users/{proxy}",
              "ConnectionType": "VPC_LINK",
              "ConnectionId": "vpc-link-id"
            },
            "RequestParameters": {
              "integration.request.path.proxy": "method.request.path.proxy"
            }
          },
          {
            "HttpMethod": "POST",
            "Integration": {
              "Type": "HTTP_PROXY",
              "IntegrationHttpMethod": "POST",
              "Uri": "http://user-service.fintech.local:8080/users"
            },
            "MethodRequestParameters": {
              "method.request.header.Authorization": true
            }
          }
        ]
      },
      {
        "PathPart": "payments",
        "HttpMethods": [
          {
            "HttpMethod": "POST",
            "Integration": {
              "Type": "HTTP_PROXY",
              "IntegrationHttpMethod": "POST",
              "Uri": "http://payment-service.fintech.local:8080/payments"
            },
            "AuthorizationType": "COGNITO_USER_POOLS",
            "AuthorizerId": "cognito-authorizer-id"
          }
        ]
      }
    ],
    "Stages": [
      {
        "StageName": "prod",
        "Description": "Production stage",
        "ThrottleSettings": {
          "RateLimit": 1000,
          "BurstLimit": 2000
        },
        "TracingConfig": {
          "TracingEnabled": true
        }
      }
    ]
  }
}
```

#### VPC Link 설정
```python
def create_vpc_link():
    """API Gateway VPC Link 생성"""
    
    apigateway_client = boto3.client('apigateway')
    
    vpc_link = apigateway_client.create_vpc_link(
        name='fintech-microservices-vpc-link',
        description='VPC link for fintech microservices',
        targetArns=[
            'arn:aws:elasticloadbalancing:ap-northeast-2:account:loadbalancer/net/microservices-nlb/1234567890abcdef'
        ]
    )
    
    return vpc_link['id']
```

### 4. 서비스 디스커버리

#### AWS Cloud Map 구성
```json
{
  "ServiceDiscoveryConfiguration": {
    "NamespaceName": "fintech.local",
    "NamespaceType": "DNS_PRIVATE",
    "VpcId": "vpc-fintech-microservices",
    "Services": [
      {
        "ServiceName": "user-service",
        "DnsConfig": {
          "DnsRecords": [
            {
              "Type": "A",
              "TTL": 60
            }
          ]
        },
        "HealthCheckCustomConfig": {
          "FailureThreshold": 3
        }
      },
      {
        "ServiceName": "payment-service",
        "DnsConfig": {
          "DnsRecords": [
            {
              "Type": "A", 
              "TTL": 60
            }
          ]
        }
      }
    ]
  }
}
```

### 5. 분산 추적 및 모니터링

#### X-Ray 트레이싱 설정
```python
# ECS 태스크에 X-Ray 사이드카 추가
xray_sidecar = {
    "name": "xray-daemon",
    "image": "amazon/aws-xray-daemon:latest",
    "essential": False,
    "cpu": 32,
    "memoryReservation": 256,
    "portMappings": [
        {
            "containerPort": 2000,
            "protocol": "udp"
        }
    ],
    "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
            "awslogs-group": "/ecs/xray-daemon",
            "awslogs-region": "ap-northeast-2",
            "awslogs-stream-prefix": "ecs"
        }
    }
}

# 애플리케이션 코드에서 X-Ray SDK 사용
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# AWS SDK 자동 추적
patch_all()

@xray_recorder.capture('user_service.get_user')
def get_user(user_id):
    # 사용자 조회 로직
    subsegment = xray_recorder.begin_subsegment('database_query')
    try:
        user = database.get_user(user_id)
        subsegment.put_metadata('user_id', user_id)
        return user
    except Exception as e:
        subsegment.add_exception(e)
        raise
    finally:
        xray_recorder.end_subsegment()
```

#### CloudWatch Container Insights
```json
{
  "ContainerInsightsConfiguration": {
    "ClusterName": "fintech-microservices-cluster",
    "EnableContainerInsights": true,
    "LogGroups": [
      "/aws/ecs/containerinsights/fintech-microservices-cluster/performance"
    ],
    "CustomMetrics": [
      {
        "MetricName": "PaymentProcessingTime",
        "Namespace": "Fintech/PaymentService",
        "Dimensions": [
          {
            "Name": "ServiceName",
            "Value": "payment-service"
          }
        ]
      }
    ]
  }
}
```

### 6. Blue/Green 배포 구현

#### CodeDeploy를 사용한 Blue/Green 배포
```python
import boto3

def setup_blue_green_deployment():
    """ECS Blue/Green 배포 설정"""
    
    codedeploy_client = boto3.client('codedeploy')
    
    # 애플리케이션 생성
    application = codedeploy_client.create_application(
        applicationName='fintech-microservices',
        computePlatform='ECS'
    )
    
    # 배포 그룹 생성
    deployment_group = codedeploy_client.create_deployment_group(
        applicationName='fintech-microservices',
        deploymentGroupName='user-service-deployment-group',
        serviceRoleArn='arn:aws:iam::account:role/CodeDeployServiceRole',
        deploymentConfigName='CodeDeployDefault.ECSBlueGreenCanary10Percent5Minutes',
        blueGreenDeploymentConfiguration={
            'terminateBlueInstancesOnDeploymentSuccess': {
                'action': 'TERMINATE',
                'terminationWaitTimeInMinutes': 5
            },
            'deploymentReadyOption': {
                'actionOnTimeout': 'CONTINUE_DEPLOYMENT'
            },
            'greenFleetProvisioningOption': {
                'action': 'COPY_AUTO_SCALING_GROUP'
            }
        },
        loadBalancerInfo={
            'targetGroupInfoList': [
                {
                    'name': 'user-service-tg-blue'
                },
                {
                    'name': 'user-service-tg-green'
                }
            ]
        },
        ecsServices=[
            {
                'serviceName': 'user-service',
                'clusterName': 'fintech-microservices-cluster'
            }
        ]
    )
    
    return deployment_group['deploymentGroupId']

# Blue/Green 배포 설정
deployment_group_id = setup_blue_green_deployment()
print(f"Deployment group created: {deployment_group_id}")
```

### 7. 보안 구성

#### 네트워크 보안
```json
{
  "SecurityGroupsConfiguration": {
    "ALBSecurityGroup": {
      "GroupName": "alb-security-group",
      "Description": "Security group for ALB",
      "IngressRules": [
        {
          "IpProtocol": "tcp",
          "FromPort": 80,
          "ToPort": 80,
          "CidrIp": "0.0.0.0/0"
        },
        {
          "IpProtocol": "tcp",
          "FromPort": 443,
          "ToPort": 443,
          "CidrIp": "0.0.0.0/0"
        }
      ]
    },
    "ECSTaskSecurityGroup": {
      "GroupName": "ecs-task-security-group",
      "Description": "Security group for ECS tasks",
      "IngressRules": [
        {
          "IpProtocol": "tcp",
          "FromPort": 8080,
          "ToPort": 8080,
          "SourceSecurityGroupId": "sg-alb-security-group"
        }
      ]
    }
  }
}
```

#### Secrets Manager 통합
```python
def setup_secrets_management():
    """Secrets Manager를 사용한 보안 정보 관리"""
    
    secrets_client = boto3.client('secretsmanager')
    
    # 데이터베이스 비밀번호
    db_secret = secrets_client.create_secret(
        Name='fintech/database/password',
        Description='Database password for fintech application',
        SecretString=json.dumps({
            'username': 'fintech_user',
            'password': 'SecurePassword123!',
            'host': 'fintech-db.cluster-xyz.ap-northeast-2.rds.amazonaws.com',
            'port': 3306,
            'database': 'fintech'
        })
    )
    
    # JWT 시크릿
    jwt_secret = secrets_client.create_secret(
        Name='fintech/auth/jwt-secret',
        Description='JWT secret for authentication',
        SecretString=json.dumps({
            'secret': 'super-secure-jwt-secret-key-256-bits'
        })
    )
    
    # API 키들
    api_keys_secret = secrets_client.create_secret(
        Name='fintech/external-apis/keys',
        Description='External API keys',
        SecretString=json.dumps({
            'payment_gateway_key': 'pg_key_123456789',
            'notification_service_key': 'ns_key_987654321'
        })
    )
    
    return {
        'db_secret_arn': db_secret['ARN'],
        'jwt_secret_arn': jwt_secret['ARN'],
        'api_keys_secret_arn': api_keys_secret['ARN']
    }

secrets = setup_secrets_management()
print(f"Secrets created: {secrets}")
```

## ❌ 다른 선택지가 부적절한 이유

### A) EC2 + Docker Swarm + ELB + CloudWatch
- **관리 복잡성**: EC2 인스턴스 및 Docker Swarm 클러스터 관리 필요
- **제한된 기능**: Docker Swarm은 Kubernetes/ECS 대비 기능 제한
- **ELB 한계**: Classic/Network LB는 컨테이너 기반 라우팅에 제한적

### C) EKS + EC2 Node Groups + Classic Load Balancer
- **운영 복잡성**: Kubernetes 클러스터 관리 오버헤드 
- **Classic LB**: 현대적 컨테이너 워크로드에 부적합
- **학습 곡선**: Kubernetes 전문 지식 필요

### D) Elastic Beanstalk + Multi-container Docker
- **플랫폼 제한**: Beanstalk의 제한된 커스터마이징
- **마이크로서비스 부적합**: 모놀리식 배포 모델에 최적화
- **확장성 한계**: 개별 서비스 스케일링 제한

## 🏗️ 완성된 마이크로서비스 아키텍처

```
┌──────────────────────────────────────────────────┐
│                    Users                         │
└─────────────────┬────────────────────────────────┘
                  │ HTTPS
┌─────────────────▼────────────────────────────────┐
│               API Gateway                        │
│        (인증, 제한, 라우팅, 변환)                   │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│          Application Load Balancer               │
│            (Layer 7 라우팅)                      │
└─────┬───────┬───────┬───────┬───────┬───────────┘
      │       │       │       │       │
┌─────▼─┐ ┌───▼─┐ ┌───▼─┐ ┌───▼─┐ ┌───▼─────┐
│ User  │ │Pay  │ │Noti │ │Trans│ │Analytics│
│Service│ │ment │ │fica │ │actio│ │ Service │
│       │ │Serv │ │tion │ │n    │ │         │
│(ECS)  │ │ice  │ │Serv │ │Serv │ │  (ECS)  │
└───┬───┘ │(ECS)│ │ice  │ │ice  │ └─────────┘
    │     └─┬───┘ │(ECS)│ │(ECS)│
    │       │     └─────┘ └─────┘
    │       │
┌───▼───────▼─────────────────────────────────────┐
│              Service Discovery                  │
│           (AWS Cloud Map)                       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                 Data Layer                      │
├─────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ RDS     │  │ ElastiC │  │ DynamoDB        │ │
│  │ MySQL   │  │ Cache   │  │ (NoSQL)         │ │
│  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              Observability                      │
├─────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ X-Ray   │  │CloudWatc│  │ Secrets         │ │
│  │(Tracing)│  │h Logs   │  │ Manager         │ │
│  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────┘
```

## 📊 성능 최적화 및 비용 관리

### 1. 자동 스케일링 전략
```python
# 커스텀 메트릭 기반 스케일링
def create_custom_scaling_policy():
    """비즈니스 메트릭 기반 스케일링"""
    
    cloudwatch = boto3.client('cloudwatch')
    autoscaling = boto3.client('application-autoscaling')
    
    # 큐 길이 기반 스케일링 메트릭
    cloudwatch.put_metric_alarm(
        AlarmName='payment-queue-length-high',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='ApproximateNumberOfMessages',
        Namespace='AWS/SQS',
        Period=300,
        Statistic='Average',
        Threshold=100.0,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:ap-northeast-2:account:payment-scaling-topic'
        ],
        Dimensions=[
            {
                'Name': 'QueueName',
                'Value': 'payment-processing-queue'
            }
        ]
    )
    
    # 응답 시간 기반 스케일링
    response_time_alarm = cloudwatch.put_metric_alarm(
        AlarmName='user-service-response-time-high',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=3,
        MetricName='TargetResponseTime',
        Namespace='AWS/ApplicationELB',
        Period=300,
        Statistic='Average',
        Threshold=2.0,  # 2초
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:application-autoscaling:ap-northeast-2:account:scalingPolicy:user-service-scale-out'
        ]
    )

create_custom_scaling_policy()
```

### 2. 비용 최적화
```json
{
  "CostOptimizationStrategy": {
    "FargateSpot": {
      "Description": "비용 절약을 위한 Fargate Spot 사용",
      "Percentage": 30,
      "Services": ["analytics-service", "batch-processing-service"]
    },
    "RightSizing": {
      "Monitoring": "CloudWatch Container Insights",
      "Adjustment": "Monthly review and optimization",
      "Target": "70-80% resource utilization"
    },
    "ScheduledScaling": {
      "BusinessHours": {
        "Min": 3,
        "Max": 20,
        "Target": 5
      },
      "OffHours": {
        "Min": 1,
        "Max": 10,
        "Target": 2
      }
    }
  }
}
```

### 3. 모니터링 대시보드
```python
def create_microservices_dashboard():
    """마이크로서비스 모니터링 대시보드"""
    
    cloudwatch = boto3.client('cloudwatch')
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/ECS", "CPUUtilization", "ServiceName", "user-service"],
                        [".", "MemoryUtilization", ".", "."],
                        ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "microservices-alb"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "ap-northeast-2",
                    "title": "Service Performance"
                }
            },
            {
                "type": "log",
                "properties": {
                    "query": "SOURCE '/ecs/user-service' | fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100",
                    "region": "ap-northeast-2",
                    "title": "Error Logs",
                    "view": "table"
                }
            }
        ]
    }
    
    dashboard = cloudwatch.put_dashboard(
        DashboardName='FinTech-Microservices-Dashboard',
        DashboardBody=json.dumps(dashboard_body)
    )
    
    return dashboard

dashboard = create_microservices_dashboard()
print(f"Dashboard created: {dashboard}")
```

## 🔧 CI/CD 파이프라인

### 1. CodePipeline을 사용한 자동 배포
```python
def create_cicd_pipeline():
    """마이크로서비스 CI/CD 파이프라인"""
    
    codepipeline = boto3.client('codepipeline')
    
    pipeline_config = {
        "pipeline": {
            "name": "user-service-pipeline",
            "roleArn": "arn:aws:iam::account:role/CodePipelineRole",
            "artifactStore": {
                "type": "S3",
                "location": "fintech-pipeline-artifacts"
            },
            "stages": [
                {
                    "name": "Source",
                    "actions": [
                        {
                            "name": "SourceAction",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "CodeCommit",
                                "version": "1"
                            },
                            "configuration": {
                                "RepositoryName": "user-service",
                                "BranchName": "main"
                            },
                            "outputArtifacts": [
                                {"name": "SourceOutput"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Build",
                    "actions": [
                        {
                            "name": "BuildAction",
                            "actionTypeId": {
                                "category": "Build",
                                "owner": "AWS",
                                "provider": "CodeBuild",
                                "version": "1"
                            },
                            "configuration": {
                                "ProjectName": "user-service-build"
                            },
                            "inputArtifacts": [
                                {"name": "SourceOutput"}
                            ],
                            "outputArtifacts": [
                                {"name": "BuildOutput"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Deploy",
                    "actions": [
                        {
                            "name": "DeployAction",
                            "actionTypeId": {
                                "category": "Deploy",
                                "owner": "AWS",
                                "provider": "CodeDeployToECS",
                                "version": "1"
                            },
                            "configuration": {
                                "ApplicationName": "fintech-microservices",
                                "DeploymentGroupName": "user-service-deployment-group"
                            },
                            "inputArtifacts": [
                                {"name": "BuildOutput"}
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    response = codepipeline.create_pipeline(**pipeline_config)
    return response['pipeline']['name']

pipeline_name = create_cicd_pipeline()
print(f"Pipeline created: {pipeline_name}")
```

### 2. 테스트 자동화
```yaml
# buildspec.yml for CodeBuild
version: 0.2
phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
      - REPOSITORY_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}
  build:
    commands:
      - echo Running unit tests...
      - mvn clean test
      - echo Running integration tests...
      - mvn integration-test
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo Writing image definitions file...
      - printf '[{"name":"user-service","imageUri":"%s"}]' $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json
artifacts:
  files:
    - imagedefinitions.json
    - appspec.yaml
    - taskdef.json
```

## 🎓 핵심 학습 포인트

1. **컨테이너 오케스트레이션**: ECS Fargate로 서버리스 컨테이너 관리
2. **마이크로서비스 통신**: API Gateway + ALB + Service Discovery
3. **무중단 배포**: Blue/Green 배포로 안전한 업데이트
4. **관찰 가능성**: X-Ray + CloudWatch로 분산 시스템 모니터링
5. **보안**: Secrets Manager + 네트워크 격리 + 최소 권한

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 컨테이너 기반 마이크로서비스 아키텍처 설계의 전형적인 예시입니다. 특히 ECS Fargate를 활용한 서버리스 컨테이너 운영과 마이크로서비스 간 통신, 그리고 관찰 가능성이 핵심 포인트입니다.

컨테이너 기반 마이크로서비스 설계 시 고려사항:

1. **오케스트레이션 플랫폼**: ECS vs EKS 선택 기준
2. **서비스 통신**: API Gateway, 로드밸런서, 서비스 메시
3. **배포 전략**: Blue/Green, Rolling, Canary 배포
4. **모니터링**: 분산 추적, 로그 집계, 메트릭 수집
5. **보안**: 컨테이너 보안, 네트워크 격리, 시크릿 관리

이로써 AWS SAA 실전 문제 풀이 시리즈 7편이 완성되었습니다. 이제 **인프라, 보안, 데이터베이스, 서버리스, 빅데이터, 하이브리드, 컨테이너**까지 모든 주요 아키텍처 패턴을 다뤘습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 실전 문제 풀이 - Auto Scaling과 Load Balancer]({% post_url 2025-06-22-aws-saa-practice-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - VPC 보안과 네트워크 ACL]({% post_url 2025-06-23-aws-saa-security-vpc-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - 데이터베이스 성능 최적화]({% post_url 2025-06-24-aws-saa-database-performance-optimization %})
- [AWS SAA 실전 문제 풀이 - 서버리스 아키텍처]({% post_url 2025-06-25-aws-saa-serverless-event-driven-architecture %})
- [AWS SAA 실전 문제 풀이 - 빅데이터 분석 아키텍처]({% post_url 2025-06-26-aws-saa-bigdata-analytics-architecture %})
- [AWS SAA 실전 문제 풀이 - 하이브리드 클라우드 마이그레이션]({% post_url 2025-06-27-aws-saa-hybrid-cloud-migration-strategy %})

**태그**: #AWS #SAA #Container #ECS #Fargate #Microservices #APIGateway #XRay #컨테이너 #마이크로서비스
