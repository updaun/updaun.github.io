---
layout: post
title: "Python Boto3 완전 가이드: AWS 리소스 관리와 자동화"
date: 2025-08-27 10:00:00 +0900
categories: [AWS, Python]
tags: [boto3, python, aws, automation, cloud, s3, ec2, lambda, iam]
---

# Python Boto3 완전 가이드: AWS 리소스 관리와 자동화

AWS의 클라우드 리소스를 프로그래밍 방식으로 관리하고 자동화할 때 가장 강력한 도구 중 하나가 바로 Python의 **Boto3** 라이브러리입니다. 이번 포스트에서는 Boto3의 기본 개념부터 실무에서 바로 활용할 수 있는 고급 사용법까지 상세하게 다뤄보겠습니다.

## 🚀 Boto3란 무엇인가?

Boto3는 Amazon Web Services(AWS)용 Python SDK입니다. AWS의 모든 서비스에 대한 Python API를 제공하여 개발자가 Python 코드로 AWS 리소스를 생성, 구성, 관리할 수 있게 해줍니다.

### 주요 특징
- **완전한 AWS 서비스 지원**: EC2, S3, Lambda, RDS 등 200개 이상의 AWS 서비스 지원
- **직관적인 API**: Python다운 객체 지향 인터페이스 제공
- **자동 재시도 및 페이징**: 네트워크 오류 처리와 대용량 데이터 처리 자동화
- **세션 관리**: 인증 정보와 설정의 체계적 관리

## 📦 Boto3 설치 및 초기 설정

### 1. 설치

```bash
pip install boto3
```

### 2. AWS 인증 정보 설정

Boto3를 사용하기 전에 AWS 인증 정보를 설정해야 합니다. 여러 방법이 있습니다:

#### 방법 1: AWS CLI를 통한 설정
```bash
aws configure
```

#### 방법 2: 환경 변수 설정
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-northeast-2
```

#### 방법 3: IAM 역할 사용 (EC2 인스턴스에서 실행시 권장)
EC2 인스턴스에 IAM 역할을 연결하면 별도의 인증 정보 없이 Boto3를 사용할 수 있습니다.

### 3. 기본 클라이언트와 리소스 생성

```python
import boto3

# 클라이언트 방식 (low-level API)
s3_client = boto3.client('s3')

# 리소스 방식 (high-level API)
s3_resource = boto3.resource('s3')

# 세션을 통한 생성
session = boto3.Session(
    aws_access_key_id='your_key',
    aws_secret_access_key='your_secret',
    region_name='ap-northeast-2'
)
s3_session_client = session.client('s3')
```

## 🏗️ 클라이언트 vs 리소스

Boto3는 두 가지 인터페이스를 제공합니다:

### 클라이언트 (Client) - Low-level API
```python
# 클라이언트 예제
s3_client = boto3.client('s3')

# S3 버킷 리스트 조회
response = s3_client.list_buckets()
print("클라이언트 응답:", response)
```

### 리소스 (Resource) - High-level API
```python
# 리소스 예제
s3_resource = boto3.resource('s3')

# 더 직관적인 방식
for bucket in s3_resource.buckets.all():
    print(f"버킷명: {bucket.name}")
```

## 💾 Amazon S3 완전 활용

### 1. 버킷 관리

```python
import boto3
from botocore.exceptions import ClientError

class S3Manager:
    def __init__(self, region_name='ap-northeast-2'):
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.s3_resource = boto3.resource('s3', region_name=region_name)
    
    def create_bucket(self, bucket_name):
        """S3 버킷 생성"""
        try:
            if self.s3_client.meta.region_name == 'us-east-1':
                # us-east-1은 LocationConstraint 불필요
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.s3_client.meta.region_name
                    }
                )
            print(f"버킷 '{bucket_name}' 생성 완료")
            return True
        except ClientError as e:
            print(f"버킷 생성 실패: {e}")
            return False
    
    def list_buckets(self):
        """모든 버킷 나열"""
        response = self.s3_client.list_buckets()
        return [bucket['Name'] for bucket in response['Buckets']]
    
    def delete_bucket(self, bucket_name):
        """버킷 삭제 (비어있어야 함)"""
        try:
            # 먼저 버킷을 비움
            self.empty_bucket(bucket_name)
            # 버킷 삭제
            self.s3_client.delete_bucket(Bucket=bucket_name)
            print(f"버킷 '{bucket_name}' 삭제 완료")
            return True
        except ClientError as e:
            print(f"버킷 삭제 실패: {e}")
            return False
    
    def empty_bucket(self, bucket_name):
        """버킷 내 모든 객체 삭제"""
        bucket = self.s3_resource.Bucket(bucket_name)
        bucket.objects.all().delete()
```

### 2. 파일 업로드/다운로드

```python
def upload_file(self, local_file_path, bucket_name, s3_key=None):
    """파일을 S3에 업로드"""
    if s3_key is None:
        s3_key = local_file_path.split('/')[-1]
    
    try:
        self.s3_client.upload_file(
            local_file_path, 
            bucket_name, 
            s3_key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'Metadata': {
                    'uploaded_by': 'boto3_script',
                    'upload_date': str(datetime.now())
                }
            }
        )
        print(f"파일 업로드 성공: {local_file_path} -> s3://{bucket_name}/{s3_key}")
        return True
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {local_file_path}")
        return False
    except ClientError as e:
        print(f"업로드 실패: {e}")
        return False

def download_file(self, bucket_name, s3_key, local_file_path):
    """S3에서 파일을 다운로드"""
    try:
        self.s3_client.download_file(bucket_name, s3_key, local_file_path)
        print(f"파일 다운로드 성공: s3://{bucket_name}/{s3_key} -> {local_file_path}")
        return True
    except ClientError as e:
        print(f"다운로드 실패: {e}")
        return False

def upload_with_progress(self, local_file_path, bucket_name, s3_key):
    """진행률을 표시하며 업로드"""
    import os
    from boto3.s3.transfer import TransferConfig
    
    def progress_callback(bytes_transferred):
        file_size = os.path.getsize(local_file_path)
        percentage = (bytes_transferred / file_size) * 100
        print(f"\r업로드 진행률: {percentage:.1f}%", end='')
    
    config = TransferConfig(
        multipart_threshold=1024 * 25,  # 25MB
        max_concurrency=10,
        multipart_chunksize=1024 * 25,
        use_threads=True
    )
    
    self.s3_client.upload_file(
        local_file_path,
        bucket_name,
        s3_key,
        Config=config,
        Callback=progress_callback
    )
    print(f"\n업로드 완료: {s3_key}")
```

### 3. S3 고급 기능 활용

```python
def setup_bucket_policy(self, bucket_name):
    """버킷 정책 설정"""
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/public/*"
            }
        ]
    }
    
    try:
        self.s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print(f"버킷 정책 설정 완료: {bucket_name}")
    except ClientError as e:
        print(f"버킷 정책 설정 실패: {e}")

def enable_versioning(self, bucket_name):
    """버킷 버전 관리 활성화"""
    self.s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    print(f"버전 관리 활성화: {bucket_name}")

def setup_lifecycle_policy(self, bucket_name):
    """수명 주기 정책 설정"""
    lifecycle_config = {
        'Rules': [
            {
                'ID': 'DeleteOldVersions',
                'Status': 'Enabled',
                'Filter': {'Prefix': 'logs/'},
                'NoncurrentVersionExpiration': {'NoncurrentDays': 30},
                'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 7}
            },
            {
                'ID': 'TransitionToIA',
                'Status': 'Enabled',
                'Filter': {'Prefix': 'archive/'},
                'Transitions': [
                    {
                        'Days': 30,
                        'StorageClass': 'STANDARD_IA'
                    },
                    {
                        'Days': 90,
                        'StorageClass': 'GLACIER'
                    }
                ]
            }
        ]
    }
    
    self.s3_client.put_bucket_lifecycle_configuration(
        Bucket=bucket_name,
        LifecycleConfiguration=lifecycle_config
    )
    print(f"수명 주기 정책 설정 완료: {bucket_name}")
```

## ⚡ Amazon EC2 관리

### 1. EC2 인스턴스 생성 및 관리

```python
class EC2Manager:
    def __init__(self, region_name='ap-northeast-2'):
        self.ec2_client = boto3.client('ec2', region_name=region_name)
        self.ec2_resource = boto3.resource('ec2', region_name=region_name)
    
    def create_instance(self, instance_config):
        """EC2 인스턴스 생성"""
        try:
            response = self.ec2_client.run_instances(
                ImageId=instance_config.get('ImageId', 'ami-0c2acfcb2ac4d02a0'),  # Amazon Linux 2
                MinCount=1,
                MaxCount=1,
                InstanceType=instance_config.get('InstanceType', 't3.micro'),
                KeyName=instance_config.get('KeyName'),
                SecurityGroupIds=instance_config.get('SecurityGroupIds', []),
                SubnetId=instance_config.get('SubnetId'),
                UserData=instance_config.get('UserData', ''),
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': instance_config.get('Tags', [
                            {'Key': 'Name', 'Value': 'Boto3-Created-Instance'}
                        ])
                    }
                ],
                IamInstanceProfile={
                    'Name': instance_config.get('IamInstanceProfile', '')
                } if instance_config.get('IamInstanceProfile') else {}
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            print(f"인스턴스 생성 시작: {instance_id}")
            
            # 인스턴스가 실행될 때까지 대기
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            print(f"인스턴스 실행 완료: {instance_id}")
            
            return instance_id
        except ClientError as e:
            print(f"인스턴스 생성 실패: {e}")
            return None
    
    def list_instances(self, filters=None):
        """EC2 인스턴스 목록 조회"""
        if filters is None:
            filters = []
        
        response = self.ec2_client.describe_instances(Filters=filters)
        instances = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_info = {
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'State': instance['State']['Name'],
                    'PublicIpAddress': instance.get('PublicIpAddress', 'N/A'),
                    'PrivateIpAddress': instance.get('PrivateIpAddress', 'N/A'),
                    'LaunchTime': instance['LaunchTime']
                }
                
                # 태그에서 이름 찾기
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_info['Name'] = tag['Value']
                        break
                
                instances.append(instance_info)
        
        return instances
    
    def stop_instance(self, instance_id):
        """인스턴스 중지"""
        try:
            self.ec2_client.stop_instances(InstanceIds=[instance_id])
            print(f"인스턴스 중지 요청: {instance_id}")
            
            # 인스턴스가 중지될 때까지 대기
            waiter = self.ec2_client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[instance_id])
            print(f"인스턴스 중지 완료: {instance_id}")
            return True
        except ClientError as e:
            print(f"인스턴스 중지 실패: {e}")
            return False
    
    def terminate_instance(self, instance_id):
        """인스턴스 종료"""
        try:
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            print(f"인스턴스 종료 요청: {instance_id}")
            return True
        except ClientError as e:
            print(f"인스턴스 종료 실패: {e}")
            return False
```

### 2. 보안 그룹 관리

```python
def create_security_group(self, group_name, description, vpc_id):
    """보안 그룹 생성"""
    try:
        response = self.ec2_client.create_security_group(
            GroupName=group_name,
            Description=description,
            VpcId=vpc_id
        )
        
        security_group_id = response['GroupId']
        print(f"보안 그룹 생성: {security_group_id}")
        
        # SSH 접근 허용 규칙 추가
        self.ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP access'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS access'}]
                }
            ]
        )
        
        return security_group_id
    except ClientError as e:
        print(f"보안 그룹 생성 실패: {e}")
        return None

def get_security_groups(self):
    """보안 그룹 목록 조회"""
    response = self.ec2_client.describe_security_groups()
    return response['SecurityGroups']
```

## 🔧 AWS Lambda 관리

```python
class LambdaManager:
    def __init__(self, region_name='ap-northeast-2'):
        self.lambda_client = boto3.client('lambda', region_name=region_name)
    
    def create_function(self, function_config):
        """Lambda 함수 생성"""
        try:
            response = self.lambda_client.create_function(
                FunctionName=function_config['FunctionName'],
                Runtime=function_config.get('Runtime', 'python3.9'),
                Role=function_config['Role'],  # IAM 역할 ARN
                Handler=function_config.get('Handler', 'lambda_function.lambda_handler'),
                Code={
                    'ZipFile': function_config.get('ZipFile', b'')  # 압축된 코드
                },
                Description=function_config.get('Description', ''),
                Timeout=function_config.get('Timeout', 30),
                MemorySize=function_config.get('MemorySize', 128),
                Environment={
                    'Variables': function_config.get('Environment', {})
                },
                Tags=function_config.get('Tags', {})
            )
            
            print(f"Lambda 함수 생성 완료: {function_config['FunctionName']}")
            return response
        except ClientError as e:
            print(f"Lambda 함수 생성 실패: {e}")
            return None
    
    def update_function_code(self, function_name, zip_file):
        """Lambda 함수 코드 업데이트"""
        try:
            response = self.lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file
            )
            print(f"Lambda 함수 코드 업데이트 완료: {function_name}")
            return response
        except ClientError as e:
            print(f"Lambda 함수 코드 업데이트 실패: {e}")
            return None
    
    def invoke_function(self, function_name, payload=None):
        """Lambda 함수 실행"""
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',  # 동기 실행
                Payload=json.dumps(payload or {})
            )
            
            result = json.loads(response['Payload'].read())
            print(f"Lambda 함수 실행 완료: {function_name}")
            return result
        except ClientError as e:
            print(f"Lambda 함수 실행 실패: {e}")
            return None
    
    def list_functions(self):
        """Lambda 함수 목록 조회"""
        response = self.lambda_client.list_functions()
        return response['Functions']
```

## 🛡️ IAM 관리

```python
class IAMManager:
    def __init__(self):
        self.iam_client = boto3.client('iam')
    
    def create_role(self, role_name, assume_role_policy, description=''):
        """IAM 역할 생성"""
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description=description
            )
            print(f"IAM 역할 생성 완료: {role_name}")
            return response['Role']
        except ClientError as e:
            print(f"IAM 역할 생성 실패: {e}")
            return None
    
    def attach_policy_to_role(self, role_name, policy_arn):
        """역할에 정책 연결"""
        try:
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"정책 연결 완료: {policy_arn} -> {role_name}")
            return True
        except ClientError as e:
            print(f"정책 연결 실패: {e}")
            return False
    
    def create_lambda_execution_role(self, role_name):
        """Lambda 실행 역할 생성"""
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        role = self.create_role(
            role_name,
            assume_role_policy,
            "Lambda 함수 실행을 위한 역할"
        )
        
        if role:
            # 기본 Lambda 실행 정책 연결
            self.attach_policy_to_role(
                role_name,
                'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
        
        return role
```

## 🚀 실무 활용 예제

### 1. 자동화된 백업 시스템

```python
import boto3
import datetime
import json
from typing import List, Dict

class AWSBackupSystem:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.ec2 = boto3.client('ec2')
        self.rds = boto3.client('rds')
    
    def backup_ec2_instances(self, tag_filters: List[Dict] = None):
        """태그 기반 EC2 인스턴스 스냅샷 생성"""
        if tag_filters is None:
            tag_filters = [
                {
                    'Name': 'tag:Environment',
                    'Values': ['production', 'staging']
                }
            ]
        
        # 백업 대상 인스턴스 조회
        response = self.ec2.describe_instances(Filters=tag_filters)
        
        backup_results = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                # 각 EBS 볼륨의 스냅샷 생성
                for block_device in instance.get('BlockDeviceMappings', []):
                    volume_id = block_device['Ebs']['VolumeId']
                    
                    snapshot_response = self.ec2.create_snapshot(
                        VolumeId=volume_id,
                        Description=f"Automated backup of {instance_id} - {datetime.datetime.now().isoformat()}",
                        TagSpecifications=[
                            {
                                'ResourceType': 'snapshot',
                                'Tags': [
                                    {'Key': 'BackupType', 'Value': 'Automated'},
                                    {'Key': 'SourceInstance', 'Value': instance_id},
                                    {'Key': 'CreatedDate', 'Value': datetime.date.today().isoformat()}
                                ]
                            }
                        ]
                    )
                    
                    backup_results.append({
                        'instance_id': instance_id,
                        'volume_id': volume_id,
                        'snapshot_id': snapshot_response['SnapshotId']
                    })
        
        return backup_results
    
    def cleanup_old_snapshots(self, retention_days: int = 7):
        """오래된 스냅샷 삭제"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        
        response = self.ec2.describe_snapshots(
            OwnerIds=['self'],
            Filters=[
                {'Name': 'tag:BackupType', 'Values': ['Automated']}
            ]
        )
        
        deleted_snapshots = []
        
        for snapshot in response['Snapshots']:
            start_time = snapshot['StartTime'].replace(tzinfo=None)
            
            if start_time < cutoff_date:
                try:
                    self.ec2.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                    deleted_snapshots.append(snapshot['SnapshotId'])
                    print(f"스냅샷 삭제: {snapshot['SnapshotId']}")
                except ClientError as e:
                    print(f"스냅샷 삭제 실패 {snapshot['SnapshotId']}: {e}")
        
        return deleted_snapshots

# 사용 예제
backup_system = AWSBackupSystem()

# 프로덕션 환경 백업
backup_results = backup_system.backup_ec2_instances([
    {'Name': 'tag:Environment', 'Values': ['production']}
])

print(f"백업 완료: {len(backup_results)}개 스냅샷 생성")

# 7일 이상된 스냅샷 정리
deleted_snapshots = backup_system.cleanup_old_snapshots(retention_days=7)
print(f"정리 완료: {len(deleted_snapshots)}개 스냅샷 삭제")
```

### 2. 비용 최적화 자동화

```python
class AWSCostOptimizer:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.ce = boto3.client('ce')  # Cost Explorer
    
    def find_idle_instances(self):
        """유휴 EC2 인스턴스 탐지"""
        cloudwatch = boto3.client('cloudwatch')
        
        # 지난 7일간의 CPU 사용률이 5% 이하인 인스턴스 찾기
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(days=7)
        
        response = self.ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        idle_instances = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                # CloudWatch에서 CPU 사용률 조회
                metrics_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[
                        {'Name': 'InstanceId', 'Value': instance_id}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1시간 단위
                    Statistics=['Average']
                )
                
                if metrics_response['Datapoints']:
                    avg_cpu = sum(dp['Average'] for dp in metrics_response['Datapoints']) / len(metrics_response['Datapoints'])
                    
                    if avg_cpu < 5.0:  # 5% 미만
                        idle_instances.append({
                            'InstanceId': instance_id,
                            'InstanceType': instance['InstanceType'],
                            'AvgCpuUtilization': avg_cpu,
                            'LaunchTime': instance['LaunchTime']
                        })
        
        return idle_instances
    
    def get_cost_by_service(self, days=30):
        """서비스별 비용 조회"""
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        response = self.ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.isoformat(),
                'End': end_date.isoformat()
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        costs = {}
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                costs[service] = cost
        
        return sorted(costs.items(), key=lambda x: x[1], reverse=True)

# 사용 예제
optimizer = AWSCostOptimizer()

# 유휴 인스턴스 탐지
idle_instances = optimizer.find_idle_instances()
print(f"유휴 인스턴스 발견: {len(idle_instances)}개")

for instance in idle_instances:
    print(f"  - {instance['InstanceId']} ({instance['InstanceType']}) "
          f"평균 CPU: {instance['AvgCpuUtilization']:.1f}%")

# 서비스별 비용 분석
costs = optimizer.get_cost_by_service()
print("\n상위 10개 서비스 비용:")
for service, cost in costs[:10]:
    print(f"  - {service}: ${cost:.2f}")
```

## ⚠️ 오류 처리 및 베스트 프랙티스

### 1. 재시도 전략

```python
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
import time
import random

# 재시도 설정
config = Config(
    region_name='ap-northeast-2',
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'  # 'legacy', 'standard', 'adaptive'
    }
)

s3_client = boto3.client('s3', config=config)

def exponential_backoff_retry(func, max_retries=3, base_delay=1):
    """지수 백오프를 사용한 재시도"""
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            # 재시도하면 안 되는 오류들
            if error_code in ['NoSuchBucket', 'AccessDenied', 'InvalidBucketName']:
                raise e
            
            if attempt == max_retries - 1:
                raise e
            
            # 지수 백오프 + 지터
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"재시도 {attempt + 1}/{max_retries} (대기: {delay:.1f}초)")
            time.sleep(delay)

# 사용 예제
def risky_operation():
    return s3_client.head_bucket(Bucket='my-test-bucket')

try:
    result = exponential_backoff_retry(risky_operation)
    print("작업 성공")
except ClientError as e:
    print(f"최종 실패: {e}")
```

### 2. 리소스 정리 패턴

```python
class AWSResourceManager:
    def __init__(self):
        self.resources_created = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 컨텍스트 매니저 종료 시 자동으로 리소스 정리
        self.cleanup_resources()
    
    def create_test_bucket(self, bucket_name):
        """테스트용 버킷 생성"""
        s3_client = boto3.client('s3')
        
        try:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': 'ap-northeast-2'
                }
            )
            self.resources_created.append(('s3_bucket', bucket_name))
            return bucket_name
        except ClientError as e:
            print(f"버킷 생성 실패: {e}")
            return None
    
    def cleanup_resources(self):
        """생성된 모든 리소스 정리"""
        for resource_type, resource_id in reversed(self.resources_created):
            try:
                if resource_type == 's3_bucket':
                    s3_client = boto3.client('s3')
                    # 버킷 비우기
                    s3_resource = boto3.resource('s3')
                    bucket = s3_resource.Bucket(resource_id)
                    bucket.objects.all().delete()
                    # 버킷 삭제
                    s3_client.delete_bucket(Bucket=resource_id)
                    print(f"버킷 삭제 완료: {resource_id}")
            except Exception as e:
                print(f"리소스 정리 실패 {resource_id}: {e}")

# 사용 예제
with AWSResourceManager() as rm:
    bucket = rm.create_test_bucket('my-test-bucket-12345')
    # 테스트 수행
    # 컨텍스트 종료 시 자동으로 버킷 삭제됨
```

## 🎯 실무 팁과 주의사항

### 1. 성능 최적화
- **페이징 처리**: 대용량 데이터 조회 시 반드시 페이징 사용
- **배치 처리**: 여러 작업을 묶어서 처리
- **캐싱**: 자주 사용하는 데이터는 캐싱 고려

### 2. 보안 고려사항
- **IAM 역할 사용**: 하드코딩된 액세스 키 대신 IAM 역할 사용
- **최소 권한 원칙**: 필요한 최소한의 권한만 부여
- **암호화**: 민감한 데이터는 반드시 암호화

### 3. 비용 관리
- **리소스 태깅**: 모든 리소스에 적절한 태그 설정
- **모니터링**: CloudWatch와 Cost Explorer 활용
- **자동화**: 불필요한 리소스 자동 정리

### 4. 로깅과 모니터링
```python
import logging
import boto3
from botocore.exceptions import ClientError

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Boto3 디버그 로깅 활성화
boto3.set_stream_logger('boto3.resources', logging.DEBUG)
boto3.set_stream_logger('botocore', logging.DEBUG)

class LoggedS3Manager:
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def upload_file_with_logging(self, local_file, bucket, key):
        """로깅을 포함한 파일 업로드"""
        try:
            logger.info(f"파일 업로드 시작: {local_file} -> s3://{bucket}/{key}")
            
            self.s3_client.upload_file(local_file, bucket, key)
            
            logger.info(f"파일 업로드 완료: {key}")
            return True
            
        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없음: {local_file}")
            return False
        except ClientError as e:
            logger.error(f"S3 업로드 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return False
```

## 📚 마무리

Boto3는 AWS 리소스를 프로그래밍 방식으로 관리하는 강력한 도구입니다. 이번 포스트에서 다룬 내용들을 요약하면:

1. **기본 설정**: 인증 정보 설정과 클라이언트/리소스 차이점
2. **S3 활용**: 파일 업로드/다운로드, 버킷 관리, 고급 기능
3. **EC2 관리**: 인스턴스 생성, 보안 그룹 설정
4. **Lambda 관리**: 함수 생성, 업데이트, 실행
5. **IAM 관리**: 역할과 정책 관리
6. **실무 예제**: 백업 자동화, 비용 최적화
7. **베스트 프랙티스**: 오류 처리, 성능 최적화, 보안

이러한 지식을 바탕으로 AWS 인프라를 효율적으로 자동화하고 관리할 수 있습니다. 시작할 때는 작은 단위부터 시작해서 점진적으로 복잡한 자동화 시스템을 구축해나가는 것을 권장합니다.

다음 포스트에서는 Boto3를 활용한 서버리스 아키텍처 구축에 대해 더 자세히 다뤄보겠습니다.

---

*이 포스트가 도움이 되셨다면, 댓글이나 이메일로 피드백을 남겨주세요! 궁금한 점이나 추가로 다뤘으면 하는 주제가 있다면 언제든 말씀해 주시기 바랍니다.*
