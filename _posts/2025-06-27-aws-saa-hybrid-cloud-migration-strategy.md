---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 하이브리드 클라우드 및 마이그레이션 전략"
date: 2025-06-27
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 하이브리드 클라우드 및 마이그레이션 전략

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 하이브리드 클라우드 및 마이그레이션 아키텍처 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 온프레미스와 AWS 클라우드 간의 연결, 데이터 마이그레이션, 그리고 점진적 클라우드 전환 전략을 다룹니다.

## 📝 실전 문제

**문제**: 한 제조업체가 온프레미스 데이터센터에서 AWS 클라우드로 점진적 마이그레이션을 계획하고 있습니다. 현재 상황과 요구사항은 다음과 같습니다:

**현재 상황:**
- 온프레미스에 200TB 데이터와 레거시 애플리케이션
- 일일 50GB 데이터 동기화 필요
- 기존 Active Directory 인증 시스템 유지
- 컴플라이언스상 일부 데이터는 온프레미스 보관 필수

**요구사항:**
- **네트워크 연결**: 안정적이고 예측 가능한 대역폭
- **데이터 마이그레이션**: 초기 200TB + 지속적 동기화
- **하이브리드 스토리지**: 온프레미스-클라우드 투명한 접근
- **인증 통합**: 기존 AD와 AWS 서비스 연동
- **점진적 마이그레이션**: 비즈니스 중단 최소화
- **재해복구**: 양방향 백업 및 복구

가장 적절한 하이브리드 클라우드 아키텍처는?

**A)** VPN Gateway + DataSync + EFS + AWS SSO

**B)** Direct Connect + AWS DataSync + Storage Gateway + AWS Directory Service + DMS

**C)** CloudFront + S3 Transfer Acceleration + EBS + IAM

**D)** Transit Gateway + Snowball Edge + FSx + AWS Organizations

## 🎯 정답 및 해설

### 정답: B

**Direct Connect + AWS DataSync + Storage Gateway + AWS Directory Service + DMS**

### 상세 분석

#### 1. 요구사항별 서비스 매핑

| 요구사항 | AWS 서비스 | 설명 |
|----------|------------|------|
| **안정적 네트워크** | **Direct Connect** | 전용 네트워크 연결, 예측 가능한 대역폭 |
| **초기 데이터 마이그레이션** | **AWS DataSync** | 대용량 데이터 효율적 전송 |
| **지속적 동기화** | **AWS DataSync** | 스케줄링된 증분 동기화 |
| **하이브리드 스토리지** | **Storage Gateway** | 온프레미스-클라우드 투명 접근 |
| **AD 통합** | **AWS Directory Service** | 기존 AD와 AWS 서비스 연동 |
| **DB 마이그레이션** | **DMS** | 최소 다운타임 DB 마이그레이션 |

#### 2. 하이브리드 아키텍처 설계 원칙

```
온프레미스 데이터센터 ←→ AWS 클라우드
├── Direct Connect (네트워크)
├── Storage Gateway (스토리지)
├── Directory Service (인증)
└── DataSync (데이터 전송)
```

## 🚀 상세 아키텍처 설계

### 1. 네트워크 연결 - AWS Direct Connect

#### Direct Connect 구성
```json
{
  "DirectConnectConfiguration": {
    "ConnectionName": "Manufacturing-DX-Primary",
    "Bandwidth": "10Gbps",
    "Location": "Seoul-DX-Location",
    "VLAN": 100,
    "BGP-ASN": 65000,
    "CustomerGateway": {
      "BGP-ASN": 65001,
      "IPAddress": "203.0.113.1"
    },
    "VirtualInterfaces": [
      {
        "Type": "Private",
        "VLAN": 100,
        "BGP-ASN": 65000,
        "CustomerAddress": "192.168.1.1/30",
        "AmazonAddress": "192.168.1.2/30",
        "VPC": "vpc-manufacturing-prod"
      },
      {
        "Type": "Transit",
        "VLAN": 200, 
        "BGP-ASN": 65000,
        "DirectConnectGateway": "dxgw-manufacturing"
      }
    ]
  }
}
```

#### 네트워크 이중화 구성
```json
{
  "RedundancyConfiguration": {
    "PrimaryConnection": {
      "ConnectionId": "dxcon-primary",
      "Location": "Seoul-DX-1",
      "Bandwidth": "10Gbps"
    },
    "SecondaryConnection": {
      "ConnectionId": "dxcon-secondary", 
      "Location": "Seoul-DX-2",
      "Bandwidth": "10Gbps"
    },
    "FailoverPolicy": {
      "BGPPriority": "AS-PATH prepending",
      "HealthCheck": "BGP keepalive"
    }
  }
}
```

### 2. 데이터 마이그레이션 - AWS DataSync

#### DataSync 태스크 구성
```json
{
  "DataSyncTask": {
    "Name": "Manufacturing-Initial-Migration",
    "SourceLocation": {
      "LocationUri": "nfs://10.0.1.100/data",
      "OnPremConfig": {
        "AgentArns": ["arn:aws:datasync:ap-northeast-2:account:agent/agent-12345"]
      }
    },
    "DestinationLocation": {
      "LocationUri": "s3://manufacturing-data-lake",
      "S3Config": {
        "BucketAccessRoleArn": "arn:aws:iam::account:role/DataSyncS3Role",
        "StorageClass": "STANDARD_IA"
      }
    },
    "Options": {
      "VerifyMode": "POINT_IN_TIME_CONSISTENT",
      "TransferMode": "CHANGED",
      "LogLevel": "TRANSFER",
      "PreserveDeletedFiles": "PRESERVE",
      "PreserveDevices": "NONE"
    },
    "Schedule": {
      "ScheduleExpression": "cron(0 2 * * ? *)"
    }
  }
}
```

#### 초기 마이그레이션 전략
```python
import boto3
import json
from datetime import datetime

def create_migration_plan():
    """단계별 마이그레이션 계획"""
    
    migration_phases = {
        "Phase1": {
            "name": "Cold Data Migration",
            "data_types": ["archived_logs", "historical_data"],
            "size": "100TB",
            "timeline": "Week 1-2",
            "storage_class": "GLACIER"
        },
        "Phase2": {
            "name": "Warm Data Migration", 
            "data_types": ["reports", "documents"],
            "size": "50TB",
            "timeline": "Week 3-4",
            "storage_class": "STANDARD_IA"
        },
        "Phase3": {
            "name": "Hot Data Migration",
            "data_types": ["active_databases", "application_data"],
            "size": "50TB", 
            "timeline": "Week 5-6",
            "storage_class": "STANDARD"
        }
    }
    
    return migration_phases

def setup_datasync_tasks(migration_phases):
    """각 단계별 DataSync 태스크 생성"""
    datasync = boto3.client('datasync')
    
    for phase_name, phase_config in migration_phases.items():
        task_config = {
            'SourceLocationArn': f'arn:aws:datasync:region:account:location/{phase_name.lower()}',
            'DestinationLocationArn': f'arn:aws:datasync:region:account:location/s3-{phase_name.lower()}',
            'Name': f'Migration-{phase_name}',
            'Options': {
                'VerifyMode': 'POINT_IN_TIME_CONSISTENT',
                'LogLevel': 'TRANSFER',
                'TransferMode': 'CHANGED'
            },
            'Tags': [
                {'Key': 'Phase', 'Value': phase_name},
                {'Key': 'Timeline', 'Value': phase_config['timeline']}
            ]
        }
        
        response = datasync.create_task(**task_config)
        print(f"Created DataSync task for {phase_name}: {response['TaskArn']}")

# 마이그레이션 실행
migration_plan = create_migration_plan()
setup_datasync_tasks(migration_plan)
```

### 3. 하이브리드 스토리지 - AWS Storage Gateway

#### File Gateway 구성
```json
{
  "StorageGatewayConfiguration": {
    "GatewayType": "FILE_S3",
    "GatewayName": "Manufacturing-FileGW",
    "ActivationKey": "activation-key-12345",
    "TimezoneId": "Asia/Seoul",
    "FileShares": [
      {
        "FileShareId": "share-manufacturing-data",
        "FileShareARN": "arn:aws:storagegateway:ap-northeast-2:account:share/share-12345",
        "S3BucketARN": "arn:aws:s3:::manufacturing-hybrid-storage",
        "Role": "arn:aws:iam::account:role/StorageGatewayRole",
        "LocationARN": "arn:aws:s3:::manufacturing-hybrid-storage",
        "DefaultStorageClass": "S3_STANDARD_IA",
        "CacheAttributes": {
          "CacheStaleTimeoutInSeconds": 300
        }
      }
    ]
  }
}
```

#### Volume Gateway 구성 (iSCSI)
```json
{
  "VolumeGatewayConfiguration": {
    "GatewayType": "STORED",
    "StoredVolumes": [
      {
        "VolumeName": "manufacturing-db-volume",
        "VolumeId": "vol-12345",
        "VolumeSizeInBytes": 1099511627776,
        "VolumeStatus": "AVAILABLE",
        "VolumeType": "STORED",
        "S3BucketARN": "arn:aws:s3:::manufacturing-volume-backups",
        "SnapshotSchedule": {
          "StartAt": 2,
          "RecurrenceInHours": 24,
          "Description": "Daily backup at 2 AM"
        }
      }
    ]
  }
}
```

### 4. 인증 통합 - AWS Directory Service

#### AWS Managed Microsoft AD
```json
{
  "DirectoryServiceConfiguration": {
    "Name": "corp.manufacturing.com",
    "Type": "MicrosoftAD",
    "Edition": "Enterprise",
    "ShortName": "CORP",
    "Password": "SecurePassword123!",
    "Description": "Manufacturing Corporate Directory",
    "VpcSettings": {
      "VpcId": "vpc-manufacturing",
      "SubnetIds": ["subnet-private-1a", "subnet-private-1c"]
    },
    "TrustSettings": {
      "TrustDirection": "Two-Way",
      "TrustType": "Forest",
      "OnPremDomainName": "onprem.manufacturing.com",
      "TrustPassword": "TrustPassword123!"
    }
  }
}
```

#### AD Connector 구성
```python
import boto3

def setup_ad_connector():
    """온프레미스 AD와 AWS 서비스 연동"""
    
    ds_client = boto3.client('ds')
    
    # AD Connector 생성
    response = ds_client.connect_directory(
        Name='onprem.manufacturing.com',
        ShortName='ONPREM',
        Password='ConnectorPassword123!',
        Description='Connection to on-premises Active Directory',
        Size='Small',
        ConnectSettings={
            'VpcId': 'vpc-manufacturing',
            'SubnetIds': ['subnet-private-1a', 'subnet-private-1c'],
            'CustomerDnsIps': ['10.0.1.10', '10.0.1.11'],
            'CustomerUserName': 'corp\\svc-aws-connector'
        }
    )
    
    directory_id = response['DirectoryId']
    
    # IAM Identity Center와 연동
    sso_client = boto3.client('sso-admin')
    
    # 권한 세트 생성
    permission_sets = [
        {
            'Name': 'ManufacturingAdmins',
            'Description': 'Full access for manufacturing admins',
            'ManagedPolicies': [
                'arn:aws:iam::aws:policy/AdministratorAccess'
            ]
        },
        {
            'Name': 'ManufacturingUsers', 
            'Description': 'Limited access for manufacturing users',
            'ManagedPolicies': [
                'arn:aws:iam::aws:policy/ReadOnlyAccess'
            ]
        }
    ]
    
    for permission_set in permission_sets:
        ps_response = sso_client.create_permission_set(
            Name=permission_set['Name'],
            Description=permission_set['Description'],
            InstanceArn='arn:aws:sso:::instance/ssoins-12345'
        )
        
        # 관리형 정책 연결
        for policy_arn in permission_set['ManagedPolicies']:
            sso_client.attach_managed_policy_to_permission_set(
                InstanceArn='arn:aws:sso:::instance/ssoins-12345',
                PermissionSetArn=ps_response['PermissionSet']['PermissionSetArn'],
                ManagedPolicyArn=policy_arn
            )
    
    return directory_id

# AD 연동 설정 실행
directory_id = setup_ad_connector()
print(f"AD Connector created: {directory_id}")
```

### 5. 데이터베이스 마이그레이션 - AWS DMS

#### DMS 복제 인스턴스
```json
{
  "DMSConfiguration": {
    "ReplicationInstanceIdentifier": "manufacturing-dms-instance",
    "ReplicationInstanceClass": "dms.r5.xlarge",
    "Engine": "postgres",
    "MultiAZ": true,
    "VpcSecurityGroupIds": ["sg-dms-replication"],
    "ReplicationSubnetGroupIdentifier": "dms-subnet-group",
    "PubliclyAccessible": false,
    "AllocatedStorage": 100,
    "StorageEncrypted": true
  }
}
```

#### DMS 마이그레이션 태스크
```python
import boto3
import json

def create_dms_migration_task():
    """DMS를 사용한 데이터베이스 마이그레이션"""
    
    dms_client = boto3.client('dms')
    
    # 소스 엔드포인트 (온프레미스 Oracle)
    source_endpoint = dms_client.create_endpoint(
        EndpointIdentifier='source-oracle-onprem',
        EndpointType='source',
        EngineName='oracle',
        Username='dms_user',
        Password='SecurePassword123!',
        ServerName='10.0.1.50',
        Port=1521,
        DatabaseName='PROD'
    )
    
    # 타겟 엔드포인트 (RDS PostgreSQL)
    target_endpoint = dms_client.create_endpoint(
        EndpointIdentifier='target-postgres-rds',
        EndpointType='target',
        EngineName='postgres',
        Username='postgres',
        Password='SecurePassword123!',
        ServerName='manufacturing-db.cluster-xyz.ap-northeast-2.rds.amazonaws.com',
        Port=5432,
        DatabaseName='manufacturing'
    )
    
    # 마이그레이션 태스크 생성
    migration_task = dms_client.create_replication_task(
        ReplicationTaskIdentifier='manufacturing-db-migration',
        SourceEndpointArn=source_endpoint['Endpoint']['EndpointArn'],
        TargetEndpointArn=target_endpoint['Endpoint']['EndpointArn'],
        ReplicationInstanceArn='arn:aws:dms:ap-northeast-2:account:rep:manufacturing-dms-instance',
        MigrationType='full-load-and-cdc',
        TableMappings=json.dumps({
            "rules": [
                {
                    "rule-type": "selection",
                    "rule-id": "1",
                    "rule-name": "1",
                    "object-locator": {
                        "schema-name": "MANUFACTURING",
                        "table-name": "%"
                    },
                    "rule-action": "include"
                }
            ]
        }),
        ReplicationTaskSettings=json.dumps({
            "TargetMetadata": {
                "TargetSchema": "public",
                "SupportLobs": True,
                "FullLobMode": False,
                "LobChunkSize": 0,
                "LimitedSizeLobMode": True,
                "LobMaxSize": 32
            },
            "FullLoadSettings": {
                "TargetTablePrepMode": "DROP_AND_CREATE",
                "CreatePkAfterFullLoad": False,
                "StopTaskCachedChangesApplied": False,
                "StopTaskCachedChangesNotApplied": False,
                "MaxFullLoadSubTasks": 8,
                "TransactionConsistencyTimeout": 600,
                "CommitRate": 10000
            },
            "Logging": {
                "EnableLogging": True,
                "LogComponents": [
                    {"Id": "TRANSFORMATION", "Severity": "LOGGER_SEVERITY_DEFAULT"},
                    {"Id": "SOURCE_UNLOAD", "Severity": "LOGGER_SEVERITY_DEFAULT"},
                    {"Id": "TARGET_LOAD", "Severity": "LOGGER_SEVERITY_DEFAULT"}
                ]
            }
        })
    )
    
    return migration_task['ReplicationTask']['ReplicationTaskArn']

# DMS 마이그레이션 실행
task_arn = create_dms_migration_task()
print(f"DMS migration task created: {task_arn}")
```

## ❌ 다른 선택지가 부적절한 이유

### A) VPN Gateway + DataSync + EFS + AWS SSO
- **네트워크 성능**: VPN은 인터넷 기반, 대역폭 불안정
- **스토리지 제한**: EFS만으로는 하이브리드 요구사항 부족
- **AD 통합 부족**: AWS SSO만으로는 기존 AD 연동 제한적

### C) CloudFront + S3 Transfer Acceleration + EBS + IAM
- **용도 불일치**: CloudFront는 CDN, 마이그레이션에 부적합
- **네트워크 연결**: 전용 네트워크 연결 부재
- **하이브리드 스토리지**: EBS는 하이브리드 스토리지 아님

### D) Transit Gateway + Snowball Edge + FSx + AWS Organizations
- **일회성 도구**: Snowball Edge는 초기 마이그레이션만, 지속적 동기화 불가
- **과도한 구성**: Organizations는 계정 관리, 마이그레이션에 직접 관련 없음

## 🏗️ 완성된 하이브리드 클라우드 아키텍처

```
┌─────────────────────────────────────────────────────┐
│              온프레미스 데이터센터                     │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Active      │  │ Oracle DB   │  │ File        │ │
│  │ Directory   │  │             │  │ Servers     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│           │               │               │         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Storage     │  │ DataSync    │  │ Direct      │ │
│  │ Gateway     │  │ Agent       │  │ Connect     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────┬───────────────┬───────────────┬───────┘
              │               │               │
              │ 10Gbps 전용선 │               │
              │               │               │
┌─────────────▼───────────────▼───────────────▼───────┐
│                  AWS 클라우드                       │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Directory   │  │ RDS         │  │ S3 Data     │ │
│  │ Service     │  │ PostgreSQL  │  │ Lake        │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│           │               │               │         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ IAM         │  │ DMS         │  │ CloudWatch  │ │
│  │ Roles       │  │ Replication │  │ Monitoring  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 📊 마이그레이션 타임라인 및 비용 최적화

### 1. 단계별 마이그레이션 계획
```python
migration_timeline = {
    "Week 1-2": {
        "tasks": [
            "Direct Connect 회선 설치",
            "Storage Gateway 배포",
            "DataSync 에이전트 설치"
        ],
        "data_migration": "Cold data (100TB) → S3 Glacier"
    },
    "Week 3-4": {
        "tasks": [
            "Directory Service 설정",
            "AD 신뢰 관계 구성",
            "IAM 역할 매핑"
        ],
        "data_migration": "Warm data (50TB) → S3 Standard-IA"
    },
    "Week 5-6": {
        "tasks": [
            "DMS 복제 인스턴스 생성",
            "데이터베이스 스키마 변환",
            "Full Load + CDC 시작"
        ],
        "data_migration": "Hot data (50TB) → S3 Standard"
    },
    "Week 7-8": {
        "tasks": [
            "애플리케이션 테스트",
            "성능 최적화",
            "재해복구 테스트"
        ],
        "cutover": "Production cutover"
    }
}
```

### 2. 비용 최적화 전략
```json
{
  "CostOptimization": {
    "Storage": {
      "S3_Intelligent_Tiering": "자동 스토리지 클래스 전환",
      "S3_Lifecycle_Policies": "90일 후 Glacier, 365일 후 Deep Archive",
      "Storage_Gateway_Cache": "온프레미스 캐시 최적화"
    },
    "Network": {
      "Direct_Connect_Commitment": "1년 약정으로 50% 절약",
      "Data_Transfer_Optimization": "CloudFront 활용한 아웃바운드 최적화"
    },
    "Compute": {
      "Reserved_Instances": "예측 가능한 워크로드에 RI 적용",
      "Spot_Instances": "개발/테스트 환경에 Spot 활용"
    }
  }
}
```

### 3. 모니터링 및 알람
```python
def setup_hybrid_monitoring():
    """하이브리드 환경 모니터링 설정"""
    
    cloudwatch = boto3.client('cloudwatch')
    
    # Direct Connect 연결 상태 모니터링
    cloudwatch.put_metric_alarm(
        AlarmName='DirectConnect-ConnectionState',
        ComparisonOperator='LessThanThreshold',
        EvaluationPeriods=2,
        MetricName='ConnectionState',
        Namespace='AWS/DX',
        Period=300,
        Statistic='Maximum',
        Threshold=1.0,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:ap-northeast-2:account:dx-alerts'
        ],
        AlarmDescription='Direct Connect connection down'
    )
    
    # DataSync 태스크 실행 모니터링
    cloudwatch.put_metric_alarm(
        AlarmName='DataSync-TaskExecution',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=1,
        MetricName='TaskExecutionResultCode',
        Namespace='AWS/DataSync',
        Period=300,
        Statistic='Maximum',
        Threshold=0.0,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:ap-northeast-2:account:datasync-alerts'
        ],
        AlarmDescription='DataSync task execution failed'
    )
    
    # Storage Gateway 성능 모니터링
    cloudwatch.put_metric_alarm(
        AlarmName='StorageGateway-CacheHitPercent',
        ComparisonOperator='LessThanThreshold',
        EvaluationPeriods=3,
        MetricName='CacheHitPercent',
        Namespace='AWS/StorageGateway',
        Period=300,
        Statistic='Average',
        Threshold=80.0,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:ap-northeast-2:account:storage-gateway-alerts'
        ],
        AlarmDescription='Storage Gateway cache hit rate low'
    )

setup_hybrid_monitoring()
```

## 🔧 재해복구 및 백업 전략

### 1. 양방향 백업 구성
```json
{
  "DisasterRecoveryStrategy": {
    "OnPremises_to_AWS": {
      "Primary": "Storage Gateway Stored Volumes",
      "Secondary": "DataSync scheduled tasks",
      "RTO": "4 hours",
      "RPO": "1 hour"
    },
    "AWS_to_OnPremises": {
      "Primary": "AWS Backup with Storage Gateway",
      "Secondary": "S3 Cross-Region Replication",
      "RTO": "6 hours", 
      "RPO": "4 hours"
    },
    "Testing": {
      "Frequency": "Monthly",
      "Scope": "Full DR simulation",
      "Automation": "Step Functions workflow"
    }
  }
}
```

### 2. 자동화된 백업 스크립트
```python
import boto3
from datetime import datetime, timedelta

def create_backup_plan():
    """AWS Backup을 사용한 자동화된 백업 계획"""
    
    backup_client = boto3.client('backup')
    
    backup_plan = {
        "BackupPlanName": "Manufacturing-Hybrid-Backup",
        "Rules": [
            {
                "RuleName": "DailyBackups",
                "TargetBackupVaultName": "manufacturing-backup-vault",
                "ScheduleExpression": "cron(0 5 ? * * *)",
                "StartWindowMinutes": 60,
                "CompletionWindowMinutes": 120,
                "Lifecycle": {
                    "MoveToColdStorageAfterDays": 30,
                    "DeleteAfterDays": 120
                },
                "RecoveryPointTags": {
                    "Environment": "Production",
                    "BackupType": "Automated"
                }
            },
            {
                "RuleName": "WeeklyLongTermBackups",
                "TargetBackupVaultName": "manufacturing-longterm-vault",
                "ScheduleExpression": "cron(0 3 ? * SUN *)",
                "StartWindowMinutes": 60,
                "CompletionWindowMinutes": 240,
                "Lifecycle": {
                    "MoveToColdStorageAfterDays": 7,
                    "DeleteAfterDays": 365
                }
            }
        ]
    }
    
    response = backup_client.create_backup_plan(BackupPlan=backup_plan)
    return response['BackupPlanId']

# 백업 계획 생성
backup_plan_id = create_backup_plan()
print(f"Backup plan created: {backup_plan_id}")
```

## 🎓 핵심 학습 포인트

1. **하이브리드 연결**: Direct Connect로 안정적 네트워크 구성
2. **점진적 마이그레이션**: 단계별 데이터/애플리케이션 이전
3. **투명한 스토리지**: Storage Gateway로 온프레미스-클라우드 통합
4. **인증 통합**: Directory Service로 기존 AD 확장
5. **최소 다운타임**: DMS로 실시간 데이터베이스 마이그레이션

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 하이브리드 클라우드 및 마이그레이션 설계의 전형적인 예시입니다. 특히 기존 온프레미스 시스템과의 연동, 점진적 마이그레이션, 그리고 비즈니스 연속성이 핵심 포인트입니다.

하이브리드 클라우드 설계 시 고려사항:

1. **네트워크 안정성**: Direct Connect vs VPN 선택 기준
2. **데이터 마이그레이션**: 대용량 초기 전송 + 지속적 동기화
3. **인증 통합**: 기존 Active Directory 활용 방안
4. **점진적 전환**: 비즈니스 중단 최소화 전략
5. **재해복구**: 양방향 백업 및 복구 체계

이로써 AWS SAA 실전 문제 풀이 시리즈 6편이 완성되었습니다. 다양한 아키텍처 패턴(고가용성, 보안, 데이터베이스, 서버리스, 빅데이터, 하이브리드)을 모두 다뤘습니다.

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

**태그**: #AWS #SAA #Hybrid-Cloud #Migration #DirectConnect #StorageGateway #DataSync #DMS #하이브리드클라우드 #마이그레이션
