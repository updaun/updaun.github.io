---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 재해 복구와 백업 전략"
date: 2025-06-29
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 재해 복구와 백업 전략

AWS Solutions Architect Associate(SAA) 시험에서 중요하게 다뤄지는 재해 복구(Disaster Recovery)와 백업 전략 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 다중 리전 아키텍처, 백업 자동화, RTO/RPO 최적화를 중심으로 다룹니다.

## 📝 실전 문제

**문제**: 한 글로벌 이커머스 회사가 기존 온프레미스 인프라를 AWS로 완전 마이그레이션한 후, 비즈니스 연속성을 위한 포괄적인 재해 복구 전략을 구축하려고 합니다. 현재 상황과 요구사항은 다음과 같습니다:

**현재 상황:**
- **주 리전**: Seoul (ap-northeast-2) - 모든 서비스 운영
- **데이터베이스**: RDS MySQL Multi-AZ (50TB), DynamoDB (10TB)
- **파일 저장소**: S3 (500TB), EFS (20TB)
- **애플리케이션**: EC2 Auto Scaling Group (10-50 인스턴스)
- **일일 거래량**: 100만 건, 연간 매출 1000억원

**요구사항:**
- **RTO (Recovery Time Objective)**: 최대 1시간
- **RPO (Recovery Point Objective)**: 최대 15분
- **DR 리전**: Tokyo (ap-northeast-1)로 설정
- **자동화**: 재해 발생 시 자동 장애조치
- **테스트**: 월 1회 DR 테스트 수행
- **비용 최적화**: DR 환경 운영 비용 최소화
- **규정 준수**: 금융 규제 요구사항 충족

가장 적절한 재해 복구 아키텍처는?

**A)** 모든 서비스를 DR 리전에 동일하게 복제 + Route 53 Health Check

**B)** RDS Cross-Region Replica + S3 Cross-Region Replication + CloudFormation + Route 53 Application Recovery Controller

**C)** AWS Backup + DataSync + Lambda 기반 자동 복구 + CloudWatch Events

**D)** DMS를 사용한 데이터 동기화 + EC2 AMI 복사 + Manual Failover

## 🎯 정답 및 해설

### 정답: B

**RDS Cross-Region Replica + S3 Cross-Region Replication + CloudFormation + Route 53 Application Recovery Controller**

### 상세 분석

#### 1. 요구사항별 서비스 매핑

| 요구사항 | AWS 서비스 | 설명 |
|----------|------------|------|
| **RTO: 1시간** | **Route 53 ARC** | 자동 장애조치, 빠른 DNS 전환 |
| **RPO: 15분** | **RDS Cross-Region Replica** | 준실시간 데이터 복제 |
| **데이터 복제** | **S3 CRR, DynamoDB Global Tables** | 자동 데이터 동기화 |
| **인프라 복원** | **CloudFormation** | 자동 리소스 프로비저닝 |
| **자동화** | **Lambda, Systems Manager** | 복구 프로세스 자동화 |
| **테스트** | **AWS Config, Trusted Advisor** | DR 테스트 및 검증 |
| **비용 최적화** | **Pilot Light 패턴** | 최소 리소스로 대기 |

#### 2. 재해 복구 패턴 선택

```
DR 패턴 비교:
┌────────────────┬─────────┬─────────┬──────────┬──────────┐
│ 패턴            │ RTO     │ RPO     │ 비용      │ 복잡도    │
├────────────────┼─────────┼─────────┼──────────┼──────────┤
│ Backup/Restore │ 시간~일  │ 시간     │ 매우 낮음 │ 낮음      │
│ Pilot Light    │ 10분~1시간│ 분~시간 │ 낮음      │ 중간      │
│ Warm Standby   │ 분      │ 초~분   │ 중간      │ 중간      │
│ Multi-Site     │ 초~분   │ 초      │ 높음      │ 높음      │
└────────────────┴─────────┴─────────┴──────────┴──────────┘

선택: Pilot Light 패턴 (RTO: 1시간, RPO: 15분 요구사항 충족)
```

## 🚀 상세 아키텍처 설계

### 1. 데이터베이스 복제 전략

#### RDS Cross-Region Read Replica
```json
{
  "RDSCrossRegionConfiguration": {
    "PrimaryDB": {
      "Region": "ap-northeast-2",
      "DBInstanceIdentifier": "ecommerce-prod-db",
      "Engine": "mysql",
      "EngineVersion": "8.0.35",
      "DBInstanceClass": "db.r6g.2xlarge",
      "AllocatedStorage": 1000,
      "StorageType": "gp3",
      "MultiAZ": true,
      "BackupRetentionPeriod": 7,
      "DeletionProtection": true
    },
    "ReadReplicas": [
      {
        "Region": "ap-northeast-1",
        "DBInstanceIdentifier": "ecommerce-dr-replica",
        "DBInstanceClass": "db.r6g.large",
        "MultiAZ": false,
        "AutoMinorVersionUpgrade": true,
        "MonitoringInterval": 60,
        "PerformanceInsightsEnabled": true
      }
    ],
    "PromotionConfiguration": {
      "AutomatedBackup": true,
      "MaxLagTime": 900,
      "MonitoringRole": "arn:aws:iam::account:role/RDSEnhancedMonitoringRole"
    }
  }
}
```

#### DynamoDB Global Tables
```python
import boto3
import json

def setup_dynamodb_global_tables():
    """DynamoDB Global Tables 설정"""
    
    dynamodb = boto3.client('dynamodb', region_name='ap-northeast-2')
    
    # 주문 테이블 Global Tables 설정
    orders_table = dynamodb.create_global_table(
        GlobalTableName='ecommerce-orders',
        ReplicationGroup=[
            {
                'RegionName': 'ap-northeast-2'
            },
            {
                'RegionName': 'ap-northeast-1'
            }
        ]
    )
    
    # 사용자 세션 테이블
    sessions_table = dynamodb.create_global_table(
        GlobalTableName='user-sessions',
        ReplicationGroup=[
            {
                'RegionName': 'ap-northeast-2'
            },
            {
                'RegionName': 'ap-northeast-1'
            }
        ]
    )
    
    # Point-in-time Recovery 활성화
    dynamodb.update_continuous_backups(
        TableName='ecommerce-orders',
        PointInTimeRecoverySpecification={
            'PointInTimeRecoveryEnabled': True
        }
    )
    
    return {
        'orders_table': orders_table['GlobalTableDescription']['GlobalTableArn'],
        'sessions_table': sessions_table['GlobalTableDescription']['GlobalTableArn']
    }

global_tables = setup_dynamodb_global_tables()
print(f"Global Tables configured: {global_tables}")
```

### 2. 스토리지 복제 구성

#### S3 Cross-Region Replication
```json
{
  "S3ReplicationConfiguration": {
    "Role": "arn:aws:iam::account:role/replication-role",
    "Rules": [
      {
        "ID": "ProductImages-CRR",
        "Status": "Enabled",
        "Priority": 1,
        "Filter": {
          "Prefix": "product-images/"
        },
        "Destination": {
          "Bucket": "arn:aws:s3:::ecommerce-dr-bucket",
          "ReplicationTime": {
            "Status": "Enabled",
            "Time": {
              "Minutes": 15
            }
          },
          "Metrics": {
            "Status": "Enabled",
            "EventThreshold": {
              "Minutes": 15
            }
          },
          "StorageClass": "STANDARD_IA"
        }
      },
      {
        "ID": "Logs-CRR",
        "Status": "Enabled",
        "Priority": 2,
        "Filter": {
          "Prefix": "logs/"
        },
        "Destination": {
          "Bucket": "arn:aws:s3:::ecommerce-dr-bucket",
          "StorageClass": "GLACIER"
        }
      }
    ]
  }
}
```

#### EFS 백업 및 복제
```python
def setup_efs_backup_replication():
    """EFS 백업 및 복제 설정"""
    
    efs_client = boto3.client('efs', region_name='ap-northeast-2')
    backup_client = boto3.client('backup', region_name='ap-northeast-2')
    
    # EFS 파일 시스템 정보
    file_system_id = 'fs-0123456789abcdef0'
    
    # 자동 백업 활성화
    efs_client.create_backup_policy(
        FileSystemId=file_system_id,
        BackupPolicy={
            'Status': 'ENABLED'
        }
    )
    
    # 백업 계획 생성
    backup_plan = backup_client.create_backup_plan(
        BackupPlan={
            'BackupPlanName': 'EFS-DR-BackupPlan',
            'Rules': [
                {
                    'RuleName': 'DailyBackups',
                    'TargetBackupVault': 'default',
                    'ScheduleExpression': 'cron(0 5 ? * * *)',
                    'StartWindowMinutes': 60,
                    'CompletionWindowMinutes': 120,
                    'Lifecycle': {
                        'MoveToColdStorageAfterDays': 30,
                        'DeleteAfterDays': 365
                    },
                    'CopyActions': [
                        {
                            'DestinationBackupVaultArn': 'arn:aws:backup:ap-northeast-1:account:backup-vault:dr-vault',
                            'Lifecycle': {
                                'MoveToColdStorageAfterDays': 30,
                                'DeleteAfterDays': 365
                            }
                        }
                    ]
                }
            ]
        }
    )
    
    # 백업 선택 생성
    backup_selection = backup_client.create_backup_selection(
        BackupPlanId=backup_plan['BackupPlanId'],
        BackupSelection={
            'SelectionName': 'EFS-Selection',
            'IamRoleArn': 'arn:aws:iam::account:role/AWSBackupDefaultServiceRole',
            'Resources': [
                f'arn:aws:elasticfilesystem:ap-northeast-2:account:file-system/{file_system_id}'
            ]
        }
    )
    
    return backup_plan['BackupPlanId']

efs_backup_plan = setup_efs_backup_replication()
print(f"EFS backup plan created: {efs_backup_plan}")
```

### 3. 인프라 자동화 (CloudFormation)

#### DR 리전 인프라 템플릿
```yaml
# dr-infrastructure.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Disaster Recovery Infrastructure for E-commerce Application'

Parameters:
  Environment:
    Type: String
    Default: 'dr'
    Description: 'Environment name'
  
  VPCCidr:
    Type: String
    Default: '10.1.0.0/16'
    Description: 'CIDR block for VPC'

Resources:
  # VPC 구성
  DRVPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VPCCidr
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-vpc'

  # 서브넷 구성
  DRPrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref DRVPC
      CidrBlock: '10.1.1.0/24'
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-private-subnet-1'

  DRPrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref DRVPC
      CidrBlock: '10.1.2.0/24'
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-private-subnet-2'

  # Launch Template (Pilot Light용 최소 구성)
  DRLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub '${Environment}-launch-template'
      LaunchTemplateData:
        ImageId: ami-0c02fb55956c7d316  # AMI는 정기적으로 업데이트
        InstanceType: t3.medium  # 평상시 최소 사양
        SecurityGroupIds:
          - !Ref DRSecurityGroup
        IamInstanceProfile:
          Arn: !GetAtt DRInstanceProfile.Arn
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum update -y
            yum install -y docker
            systemctl start docker
            systemctl enable docker
            # Application deployment scripts
            aws s3 cp s3://ecommerce-deployment-scripts/deploy.sh /tmp/
            chmod +x /tmp/deploy.sh
            /tmp/deploy.sh

  # Auto Scaling Group (Pilot Light - 최소 용량)
  DRAutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: !Sub '${Environment}-asg'
      LaunchTemplate:
        LaunchTemplateId: !Ref DRLaunchTemplate
        Version: !GetAtt DRLaunchTemplate.LatestVersionNumber
      MinSize: 0  # Pilot Light - 평상시 0대
      MaxSize: 50
      DesiredCapacity: 0
      VPCZoneIdentifier:
        - !Ref DRPrivateSubnet1
        - !Ref DRPrivateSubnet2
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-instance'
          PropagateAtLaunch: true

  # Application Load Balancer
  DRALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub '${Environment}-alb'
      Type: application
      Scheme: internet-facing
      SecurityGroups:
        - !Ref DRALBSecurityGroup
      Subnets:
        - !Ref DRPublicSubnet1
        - !Ref DRPublicSubnet2

  # 기타 리소스들...

Outputs:
  VPCId:
    Description: 'DR VPC ID'
    Value: !Ref DRVPC
    Export:
      Name: !Sub '${Environment}-vpc-id'
  
  LoadBalancerDNS:
    Description: 'DR Load Balancer DNS'
    Value: !GetAtt DRALB.DNSName
    Export:
      Name: !Sub '${Environment}-alb-dns'
```

### 4. Route 53 Application Recovery Controller

#### ARC 클러스터 및 컨트롤 패널 설정
```python
def setup_route53_arc():
    """Route 53 Application Recovery Controller 설정"""
    
    arc_client = boto3.client('route53-recovery-cluster')
    control_client = boto3.client('route53-recovery-control-config')
    
    # 클러스터 생성
    cluster = control_client.create_cluster(
        ClusterName='ecommerce-dr-cluster'
    )
    
    cluster_arn = cluster['Cluster']['ClusterArn']
    
    # 컨트롤 패널 생성
    control_panel = control_client.create_control_panel(
        ClusterArn=cluster_arn,
        ControlPanelName='ecommerce-failover-panel'
    )
    
    # 라우팅 컨트롤 생성
    primary_control = control_client.create_routing_control(
        ClusterArn=cluster_arn,
        ControlPanelArn=control_panel['ControlPanel']['ControlPanelArn'],
        RoutingControlName='primary-region-control'
    )
    
    dr_control = control_client.create_routing_control(
        ClusterArn=cluster_arn,
        ControlPanelArn=control_panel['ControlPanel']['ControlPanelArn'],
        RoutingControlName='dr-region-control'
    )
    
    # 안전 규칙 생성 (동시에 두 리전이 활성화되지 않도록)
    safety_rule = control_client.create_safety_rule(
        AssertionRule={
            'Name': 'one-region-only',
            'ControlPanelArn': control_panel['ControlPanel']['ControlPanelArn'],
            'WaitPeriodMs': 5000,
            'AssertedControls': [
                primary_control['RoutingControl']['RoutingControlArn'],
                dr_control['RoutingControl']['RoutingControlArn']
            ],
            'RuleConfig': {
                'Type': 'ATLEAST',
                'Threshold': 1,
                'Inverted': False
            }
        }
    )
    
    return {
        'cluster_arn': cluster_arn,
        'primary_control_arn': primary_control['RoutingControl']['RoutingControlArn'],
        'dr_control_arn': dr_control['RoutingControl']['RoutingControlArn']
    }

arc_config = setup_route53_arc()
print(f"Route 53 ARC configured: {arc_config}")
```

#### Route 53 Health Check 및 레코드 설정
```python
def setup_route53_failover():
    """Route 53 장애조치 설정"""
    
    route53 = boto3.client('route53')
    
    # 주 리전 Health Check
    primary_health_check = route53.create_health_check(
        Type='HTTPS',
        ResourcePath='/health',
        FullyQualifiedDomainName='ecommerce-primary-alb.ap-northeast-2.elb.amazonaws.com',
        Port=443,
        RequestInterval=30,
        FailureThreshold=3
    )
    
    # DR 리전 Health Check
    dr_health_check = route53.create_health_check(
        Type='HTTPS',
        ResourcePath='/health',
        FullyQualifiedDomainName='ecommerce-dr-alb.ap-northeast-1.elb.amazonaws.com',
        Port=443,
        RequestInterval=30,
        FailureThreshold=3
    )
    
    # 주 리전 레코드 (PRIMARY)
    primary_record = route53.change_resource_record_sets(
        HostedZoneId='Z1234567890',
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': 'ecommerce.example.com',
                        'Type': 'A',
                        'SetIdentifier': 'primary',
                        'Failover': 'PRIMARY',
                        'AliasTarget': {
                            'DNSName': 'ecommerce-primary-alb.ap-northeast-2.elb.amazonaws.com',
                            'EvaluateTargetHealth': True,
                            'HostedZoneId': 'Z14GRHDCWA56QT'  # Seoul ELB Hosted Zone
                        },
                        'HealthCheckId': primary_health_check['HealthCheck']['Id']
                    }
                }
            ]
        }
    )
    
    # DR 리전 레코드 (SECONDARY)
    dr_record = route53.change_resource_record_sets(
        HostedZoneId='Z1234567890',
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': 'ecommerce.example.com',
                        'Type': 'A',
                        'SetIdentifier': 'dr',
                        'Failover': 'SECONDARY',
                        'AliasTarget': {
                            'DNSName': 'ecommerce-dr-alb.ap-northeast-1.elb.amazonaws.com',
                            'EvaluateTargetHealth': True,
                            'HostedZoneId': 'Z2M4EHUR26P7ZW'  # Tokyo ELB Hosted Zone
                        },
                        'HealthCheckId': dr_health_check['HealthCheck']['Id']
                    }
                }
            ]
        }
    )
    
    return {
        'primary_health_check_id': primary_health_check['HealthCheck']['Id'],
        'dr_health_check_id': dr_health_check['HealthCheck']['Id']
    }

route53_config = setup_route53_failover()
print(f"Route 53 failover configured: {route53_config}")
```

### 5. 자동 장애조치 Lambda 함수

#### 장애 감지 및 복구 자동화
```python
import boto3
import json
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    자동 장애조치 Lambda 함수
    CloudWatch Alarm 또는 Health Check 실패 시 호출
    """
    
    print(f"Disaster recovery event received: {json.dumps(event)}")
    
    # AWS 클라이언트 초기화
    rds_client = boto3.client('rds', region_name='ap-northeast-1')
    asg_client = boto3.client('autoscaling', region_name='ap-northeast-1')
    cfn_client = boto3.client('cloudformation', region_name='ap-northeast-1')
    sns_client = boto3.client('sns')
    
    try:
        # 1. RDS Read Replica 승격
        promote_response = promote_rds_replica(rds_client)
        
        # 2. Auto Scaling Group 활성화
        scale_response = activate_auto_scaling_group(asg_client)
        
        # 3. 추가 인프라 프로비저닝
        infra_response = provision_additional_infrastructure(cfn_client)
        
        # 4. 알림 발송
        notification_response = send_disaster_notification(sns_client, {
            'rds_promotion': promote_response,
            'asg_activation': scale_response,
            'infrastructure': infra_response
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Disaster recovery completed successfully',
                'rds_promotion': promote_response,
                'asg_activation': scale_response,
                'infrastructure': infra_response
            })
        }
        
    except Exception as e:
        print(f"Error during disaster recovery: {str(e)}")
        
        # 실패 알림
        sns_client.publish(
            TopicArn=os.environ['ALERT_TOPIC_ARN'],
            Subject='CRITICAL: Disaster Recovery Failed',
            Message=f'Automatic disaster recovery failed: {str(e)}'
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Disaster recovery failed',
                'error': str(e)
            })
        }

def promote_rds_replica(rds_client) -> Dict[str, Any]:
    """RDS Read Replica를 Primary로 승격"""
    
    replica_identifier = 'ecommerce-dr-replica'
    
    try:
        # Read Replica 승격
        response = rds_client.promote_read_replica(
            DBInstanceIdentifier=replica_identifier
        )
        
        # 승격 완료까지 대기
        waiter = rds_client.get_waiter('db_instance_available')
        waiter.wait(
            DBInstanceIdentifier=replica_identifier,
            WaiterConfig={
                'Delay': 30,
                'MaxAttempts': 20
            }
        )
        
        print(f"RDS replica {replica_identifier} promoted successfully")
        return {
            'status': 'success',
            'db_instance': replica_identifier,
            'endpoint': response['DBInstance']['Endpoint']['Address']
        }
        
    except Exception as e:
        print(f"Failed to promote RDS replica: {str(e)}")
        raise

def activate_auto_scaling_group(asg_client) -> Dict[str, Any]:
    """Auto Scaling Group 활성화 (Pilot Light → Active)"""
    
    asg_name = 'dr-asg'
    
    try:
        # Auto Scaling Group 용량 증가
        response = asg_client.update_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            MinSize=2,
            DesiredCapacity=5,
            MaxSize=50
        )
        
        # 인스턴스 시작 대기
        waiter = asg_client.get_waiter('auto_scaling_group_exists')
        waiter.wait(AutoScalingGroupNames=[asg_name])
        
        print(f"Auto Scaling Group {asg_name} activated")
        return {
            'status': 'success',
            'asg_name': asg_name,
            'desired_capacity': 5
        }
        
    except Exception as e:
        print(f"Failed to activate Auto Scaling Group: {str(e)}")
        raise

def provision_additional_infrastructure(cfn_client) -> Dict[str, Any]:
    """추가 인프라 프로비저닝 (ElastiCache, EFS 등)"""
    
    stack_name = 'dr-additional-infrastructure'
    template_url = 'https://s3.amazonaws.com/ecommerce-templates/dr-additional.yaml'
    
    try:
        # CloudFormation 스택 생성
        response = cfn_client.create_stack(
            StackName=stack_name,
            TemplateURL=template_url,
            Parameters=[
                {
                    'ParameterKey': 'Environment',
                    'ParameterValue': 'dr-active'
                }
            ],
            Capabilities=['CAPABILITY_IAM']
        )
        
        # 스택 생성 완료 대기
        waiter = cfn_client.get_waiter('stack_create_complete')
        waiter.wait(
            StackName=stack_name,
            WaiterConfig={
                'Delay': 30,
                'MaxAttempts': 60
            }
        )
        
        print(f"Additional infrastructure stack {stack_name} created")
        return {
            'status': 'success',
            'stack_name': stack_name,
            'stack_id': response['StackId']
        }
        
    except Exception as e:
        print(f"Failed to provision additional infrastructure: {str(e)}")
        raise

def send_disaster_notification(sns_client, recovery_details: Dict[str, Any]) -> Dict[str, Any]:
    """재해 복구 완료 알림"""
    
    topic_arn = os.environ['NOTIFICATION_TOPIC_ARN']
    
    message = f"""
    🚨 DISASTER RECOVERY ACTIVATED 🚨
    
    Automatic disaster recovery has been completed successfully.
    
    Details:
    - RDS Promotion: {recovery_details['rds_promotion']['status']}
    - Auto Scaling: {recovery_details['asg_activation']['status']}
    - Infrastructure: {recovery_details['infrastructure']['status']}
    
    New Database Endpoint: {recovery_details['rds_promotion'].get('endpoint', 'N/A')}
    Active Instances: {recovery_details['asg_activation'].get('desired_capacity', 'N/A')}
    
    Please verify all services are functioning correctly.
    """
    
    response = sns_client.publish(
        TopicArn=topic_arn,
        Subject='Disaster Recovery Completed',
        Message=message
    )
    
    return {'status': 'success', 'message_id': response['MessageId']}
```

### 6. 모니터링 및 알림

#### CloudWatch 알람 설정
```python
def setup_dr_monitoring():
    """재해 복구 모니터링 설정"""
    
    cloudwatch = boto3.client('cloudwatch', region_name='ap-northeast-2')
    
    # RDS 복제 지연 모니터링
    rds_lag_alarm = cloudwatch.put_metric_alarm(
        AlarmName='RDS-Replica-Lag-High',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='ReplicaLag',
        Namespace='AWS/RDS',
        Period=300,
        Statistic='Average',
        Threshold=900.0,  # 15분
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:ap-northeast-2:account:dr-alerts'
        ],
        AlarmDescription='RDS Replica lag is too high',
        Dimensions=[
            {
                'Name': 'DBInstanceIdentifier',
                'Value': 'ecommerce-dr-replica'
            }
        ]
    )
    
    # S3 복제 지연 모니터링
    s3_replication_alarm = cloudwatch.put_metric_alarm(
        AlarmName='S3-Replication-Failed',
        ComparisonOperator='LessThanThreshold',
        EvaluationPeriods=3,
        MetricName='ReplicationLatency',
        Namespace='AWS/S3',
        Period=900,
        Statistic='Average',
        Threshold=900.0,  # 15분
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:ap-northeast-2:account:dr-alerts'
        ]
    )
    
    # 애플리케이션 Health Check 실패
    app_health_alarm = cloudwatch.put_metric_alarm(
        AlarmName='Application-Health-Check-Failed',
        ComparisonOperator='LessThanThreshold',
        EvaluationPeriods=3,
        MetricName='HealthyHostCount',
        Namespace='AWS/ApplicationELB',
        Period=60,
        Statistic='Average',
        Threshold=1.0,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:lambda:ap-northeast-2:account:function:disaster-recovery-trigger'
        ]
    )
    
    return {
        'rds_lag_alarm': rds_lag_alarm,
        's3_replication_alarm': s3_replication_alarm,
        'app_health_alarm': app_health_alarm
    }

monitoring_config = setup_dr_monitoring()
print(f"DR monitoring configured: {monitoring_config}")
```

### 7. DR 테스트 자동화

#### 월간 DR 테스트 스크립트
```python
import boto3
import json
import time
from datetime import datetime, timedelta

def monthly_dr_test():
    """월간 DR 테스트 실행"""
    
    print("Starting monthly DR test...")
    
    # 테스트 시작 시간
    test_start_time = datetime.now()
    
    try:
        # 1. DR 환경 활성화 (테스트 모드)
        test_activation = activate_dr_test_environment()
        
        # 2. 데이터 일관성 검증
        data_consistency = verify_data_consistency()
        
        # 3. 애플리케이션 기능 테스트
        app_functionality = test_application_functionality()
        
        # 4. 성능 테스트
        performance_test = run_performance_tests()
        
        # 5. RTO/RPO 측정
        rto_rpo_metrics = measure_rto_rpo()
        
        # 6. 테스트 환경 정리
        cleanup_response = cleanup_test_environment()
        
        # 테스트 종료 시간
        test_end_time = datetime.now()
        test_duration = (test_end_time - test_start_time).total_seconds()
        
        # 테스트 결과 리포트 생성
        test_report = generate_test_report({
            'test_start_time': test_start_time.isoformat(),
            'test_end_time': test_end_time.isoformat(),
            'test_duration_seconds': test_duration,
            'test_activation': test_activation,
            'data_consistency': data_consistency,
            'app_functionality': app_functionality,
            'performance_test': performance_test,
            'rto_rpo_metrics': rto_rpo_metrics,
            'cleanup': cleanup_response
        })
        
        # 리포트 전송
        send_test_report(test_report)
        
        return test_report
        
    except Exception as e:
        error_report = {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        
        # 실패 알림
        send_test_failure_notification(error_report)
        
        return error_report

def activate_dr_test_environment():
    """DR 테스트 환경 활성화"""
    
    cfn_client = boto3.client('cloudformation', region_name='ap-northeast-1')
    
    # 테스트용 스택 생성
    response = cfn_client.create_stack(
        StackName='dr-test-environment',
        TemplateURL='https://s3.amazonaws.com/ecommerce-templates/dr-test.yaml',
        Parameters=[
            {
                'ParameterKey': 'Environment',
                'ParameterValue': 'dr-test'
            },
            {
                'ParameterKey': 'TestMode',
                'ParameterValue': 'true'
            }
        ]
    )
    
    # 스택 생성 대기
    waiter = cfn_client.get_waiter('stack_create_complete')
    waiter.wait(StackName='dr-test-environment')
    
    return {'status': 'success', 'stack_id': response['StackId']}

def verify_data_consistency():
    """데이터 일관성 검증"""
    
    # RDS 데이터 검증
    rds_check = verify_rds_data_consistency()
    
    # DynamoDB 데이터 검증
    dynamodb_check = verify_dynamodb_data_consistency()
    
    # S3 데이터 검증
    s3_check = verify_s3_data_consistency()
    
    return {
        'rds': rds_check,
        'dynamodb': dynamodb_check,
        's3': s3_check,
        'overall_status': 'pass' if all([
            rds_check['status'] == 'pass',
            dynamodb_check['status'] == 'pass',
            s3_check['status'] == 'pass'
        ]) else 'fail'
    }

def generate_test_report(test_results):
    """DR 테스트 리포트 생성"""
    
    report = {
        'test_id': f"dr-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        'test_date': test_results['test_start_time'],
        'duration_minutes': round(test_results['test_duration_seconds'] / 60, 2),
        'rto_achieved': test_results['rto_rpo_metrics']['rto_seconds'],
        'rpo_achieved': test_results['rto_rpo_metrics']['rpo_seconds'],
        'rto_target': 3600,  # 1시간
        'rpo_target': 900,   # 15분
        'test_results': test_results,
        'recommendations': generate_recommendations(test_results),
        'next_test_date': (datetime.now() + timedelta(days=30)).isoformat()
    }
    
    # S3에 리포트 저장
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket='ecommerce-dr-reports',
        Key=f"monthly-tests/{report['test_id']}.json",
        Body=json.dumps(report, indent=2),
        ContentType='application/json'
    )
    
    return report

# Lambda 함수로 매월 실행
def lambda_handler(event, context):
    """월간 DR 테스트 Lambda 핸들러"""
    return monthly_dr_test()
```

## ❌ 다른 선택지가 부적절한 이유

### A) 모든 서비스를 DR 리전에 동일하게 복제
- **비용 과다**: 100% 리소스 복제로 운영 비용 2배 증가
- **과도한 설계**: RTO 1시간 요구사항에 비해 과도한 투자
- **관리 복잡성**: 두 리전의 동일한 인프라 관리 부담

### C) AWS Backup + DataSync + Lambda 기반 자동 복구
- **RTO 미달**: 백업 복원 방식은 1시간 RTO 달성 어려움
- **RPO 제한**: 정기 백업으로는 15분 RPO 불가능
- **제한된 자동화**: 완전 자동 장애조치 구현 복잡

### D) DMS + EC2 AMI 복사 + Manual Failover
- **수동 처리**: Manual Failover로 RTO 목표 달성 불가
- **DMS 한계**: 실시간 동기화에 비해 지연 발생 가능
- **AMI 방식**: EC2 AMI 복사는 최신 상태 반영 지연

## 🏗️ 완성된 재해 복구 아키텍처

```
주 리전 (Seoul - ap-northeast-2)
┌─────────────────────────────────────────────────┐
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Route 53  │    │      CloudWatch         │ │
│  │ Health Check│    │    Monitoring &         │ │
│  │             │    │      Alarms             │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │    ALB      │    │      EC2 Auto           │ │
│  │             │    │    Scaling Group        │ │
│  │             │    │    (10-50 instances)    │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │ RDS MySQL   │    │      DynamoDB           │ │
│  │  Multi-AZ   │═══▶│   Global Tables         │ │
│  │   (50TB)    │    │     (10TB)              │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │     S3      │    │        EFS              │ │
│  │   (500TB)   │═══▶│       (20TB)            │ │
│  │   Primary   │    │                         │ │
│  └─────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────┘
                          │
                    Cross-Region
                    Replication
                          │
                          ▼
DR 리전 (Tokyo - ap-northeast-1)
┌─────────────────────────────────────────────────┐
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Route 53  │    │ Application Recovery    │ │
│  │ Failover    │    │     Controller          │ │
│  │             │    │                         │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │    ALB      │    │      EC2 Auto           │ │
│  │  (Standby)  │    │    Scaling Group        │ │
│  │             │    │  (Pilot Light: 0→50)    │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │ RDS MySQL   │    │      DynamoDB           │ │
│  │Read Replica │    │   Global Tables         │ │
│  │   (50TB)    │    │     (10TB)              │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │     S3      │    │      EFS Backup         │ │
│  │   (500TB)   │    │      & Restore          │ │
│  │  Replica    │    │                         │ │
│  └─────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────┘

자동 장애조치 플로우:
1. Health Check 실패 감지
2. Lambda 함수 트리거
3. RDS Read Replica 승격
4. Auto Scaling Group 활성화
5. Route 53 DNS 전환
6. 알림 및 모니터링
```

## 📊 비용 최적화 및 성능 분석

### 1. 비용 분석
```python
def calculate_dr_costs():
    """DR 환경 비용 계산"""
    
    monthly_costs = {
        'rds_replica': {
            'instance': 500,  # db.r6g.large
            'storage': 200,   # 50TB * $0.115/GB/month
            'backup': 50      # 백업 스토리지
        },
        's3_replication': {
            'storage_standard_ia': 300,  # 500TB * $0.0125/GB/month
            'replication_requests': 20,
            'data_transfer': 100
        },
        'dynamodb_global_tables': {
            'write_replicated_units': 150,
            'storage': 100
        },
        'pilot_light_infrastructure': {
            'alb': 25,
            'nat_gateway': 45,
            'vpc_endpoints': 30
        },
        'monitoring_and_automation': {
            'cloudwatch': 50,
            'lambda': 10,
            'sns': 5
        }
    }
    
    total_monthly_cost = sum(
        sum(service.values()) 
        for service in monthly_costs.values()
    )
    
    # 주 환경 비용 대비 DR 비용 비율
    primary_monthly_cost = 10000  # 가정
    dr_cost_ratio = (total_monthly_cost / primary_monthly_cost) * 100
    
    return {
        'monthly_costs': monthly_costs,
        'total_monthly_cost': total_monthly_cost,
        'dr_cost_ratio_percent': dr_cost_ratio,
        'annual_cost': total_monthly_cost * 12
    }

cost_analysis = calculate_dr_costs()
print(f"DR Cost Analysis: {json.dumps(cost_analysis, indent=2)}")
```

### 2. RTO/RPO 최적화
```json
{
  "RTOOptimization": {
    "Target": "1 hour",
    "Components": [
      {
        "Component": "RDS Read Replica Promotion",
        "EstimatedTime": "5-10 minutes",
        "Optimization": "Multi-AZ replica for faster promotion"
      },
      {
        "Component": "Auto Scaling Group Activation",
        "EstimatedTime": "10-15 minutes",
        "Optimization": "Pre-warmed AMIs, faster instance startup"
      },
      {
        "Component": "Application Deployment",
        "EstimatedTime": "5-10 minutes",
        "Optimization": "Container-based deployment"
      },
      {
        "Component": "DNS Propagation",
        "EstimatedTime": "2-5 minutes",
        "Optimization": "Low TTL values, Route 53 ARC"
      }
    ],
    "TotalEstimatedRTO": "22-40 minutes",
    "Buffer": "20-38 minutes"
  },
  "RPOOptimization": {
    "Target": "15 minutes",
    "Components": [
      {
        "Component": "RDS Replication",
        "AchievedRPO": "< 1 minute",
        "Method": "Asynchronous replication"
      },
      {
        "Component": "DynamoDB Global Tables",
        "AchievedRPO": "< 1 second",
        "Method": "Multi-master replication"
      },
      {
        "Component": "S3 Cross-Region Replication",
        "AchievedRPO": "< 15 minutes",
        "Method": "Real-time replication with RTC"
      },
      {
        "Component": "EFS Backup",
        "AchievedRPO": "1 hour",
        "Method": "Automated daily backups"
      }
    ]
  }
}
```

### 3. 보안 및 규정 준수
```python
def implement_compliance_controls():
    """규정 준수를 위한 보안 제어 구현"""
    
    # 데이터 암호화
    encryption_config = {
        'rds': {
            'encryption_at_rest': True,
            'encryption_in_transit': True,
            'kms_key': 'arn:aws:kms:region:account:key/12345678-1234-1234-1234-123456789012'
        },
        's3': {
            'default_encryption': 'AES256',
            'bucket_key': True,
            'ssl_only': True
        },
        'dynamodb': {
            'encryption_at_rest': True,
            'customer_managed_key': True
        }
    }
    
    # 액세스 제어
    iam_policies = {
        'dr_execution_role': {
            'actions': [
                'rds:PromoteReadReplica',
                'autoscaling:UpdateAutoScalingGroup',
                'cloudformation:CreateStack',
                'route53:ChangeResourceRecordSets'
            ],
            'conditions': {
                'source_ip': ['10.0.0.0/8'],
                'mfa_required': True
            }
        }
    }
    
    # 감사 로깅
    audit_config = {
        'cloudtrail': {
            'multi_region': True,
            'log_file_validation': True,
            'event_selectors': ['*']
        },
        'config': {
            'configuration_recorder': True,
            'compliance_rules': [
                'rds-encryption-enabled',
                's3-bucket-ssl-requests-only',
                'dynamodb-encryption-enabled'
            ]
        }
    }
    
    return {
        'encryption': encryption_config,
        'iam_policies': iam_policies,
        'audit': audit_config
    }

compliance_config = implement_compliance_controls()
print(f"Compliance controls: {json.dumps(compliance_config, indent=2)}")
```

## 🎓 핵심 학습 포인트

1. **재해 복구 패턴**: Pilot Light로 비용 효율적인 DR 구현
2. **자동화**: Lambda 기반 자동 장애조치로 RTO 단축
3. **데이터 복제**: 다중 서비스의 크로스 리전 복제 전략
4. **모니터링**: 포괄적인 Health Check와 알람 시스템
5. **테스트**: 정기적인 DR 테스트로 실효성 검증

## 💭 마무리

이 문제는 AWS SAA 시험에서 핵심적으로 다뤄지는 재해 복구 설계의 종합적인 예시입니다. 특히 RTO/RPO 요구사항을 만족하면서도 비용 효율적인 Pilot Light 패턴의 구현이 핵심 포인트입니다.

재해 복구 설계 시 고려사항:

1. **비즈니스 요구사항**: RTO/RPO 목표 설정
2. **비용 최적화**: 적절한 DR 패턴 선택
3. **자동화**: 사람의 개입 최소화
4. **테스트**: 정기적인 DR 드릴 수행
5. **규정 준수**: 보안 및 감사 요구사항

이로써 AWS SAA 실전 문제 풀이 시리즈 8편이 완성되었습니다. 이제 **인프라, 보안, 데이터베이스, 서버리스, 빅데이터, 하이브리드, 컨테이너, 재해복구**까지 모든 주요 AWS 아키텍처 패턴을 다뤘습니다.

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
- [AWS SAA 실전 문제 풀이 - 컨테이너 마이크로서비스]({% post_url 2025-06-28-aws-saa-container-microservices-architecture %})

**태그**: #AWS #SAA #DisasterRecovery #Backup #RTO #RPO #Route53 #RDS #CrossRegion #재해복구
