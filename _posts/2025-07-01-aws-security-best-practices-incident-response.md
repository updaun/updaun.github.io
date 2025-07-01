---
layout: post
title: "AWS 보안 모범 사례와 실제 보안 사고 대응 전략"
date: 2025-07-01 10:00:00 +0900
categories: [AWS, Security]
tags: [AWS, Security, IAM, CloudTrail, GuardDuty, IncidentResponse, 보안, 사고대응, 모범사례]
---

# AWS 보안 모범 사례와 실제 보안 사고 대응 전략

클라우드 환경에서 보안은 가장 중요한 요소 중 하나입니다. 이번 포스트에서는 AWS 환경에서 발생할 수 있는 실제 보안 위협과 사고 시나리오를 바탕으로, 효과적인 보안 모범 사례와 체계적인 사고 대응 전략을 다뤄보겠습니다.

## 🚨 실제 보안 사고 시나리오

### 사고 1: AWS 액세스 키 유출

**상황**: 개발자가 실수로 GitHub 공개 리포지토리에 AWS 액세스 키를 커밋했고, 해커가 이를 발견하여 EC2 인스턴스를 대량 생성하고 암호화폐 마이닝을 시작했습니다.

**피해 규모**:
- 100개의 c5.24xlarge 인스턴스 생성
- 6시간 동안 약 $18,000의 비용 발생
- 일부 프로덕션 데이터에 무단 접근

### 사고 2: 권한 에스컬레이션 공격

**상황**: 내부 직원의 계정이 피싱 공격으로 탈취되었고, 공격자가 IAM 권한을 점진적으로 확대하여 결국 관리자 권한을 얻었습니다.

**공격 경로**:
1. 피싱 이메일로 직원 계정 탈취
2. EC2 인스턴스의 IAM 역할 탈취
3. AssumeRole을 통한 권한 확대
4. 관리자 정책 연결로 전체 권한 획득

## 🛡️ 다층 보안 방어 체계 구축

### 1. Identity and Access Management (IAM) 강화

#### 최소 권한 원칙 구현
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket/user-data/${aws:username}/*"
      ],
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

#### IAM 정책 분석 자동화
```python
import boto3
import json
from datetime import datetime, timedelta

class IAMSecurityAuditor:
    def __init__(self):
        self.iam = boto3.client('iam')
        self.access_analyzer = boto3.client('accessanalyzer')
    
    def audit_excessive_permissions(self):
        """과도한 권한을 가진 사용자/역할 감지"""
        high_risk_actions = [
            'iam:*',
            '*:*',
            'iam:CreateUser',
            'iam:AttachUserPolicy',
            'iam:CreateRole',
            'ec2:*',
            's3:*'
        ]
        
        risky_entities = []
        
        # 사용자 정책 검사
        users = self.iam.list_users()['Users']
        for user in users:
            user_policies = self._get_user_policies(user['UserName'])
            risk_score = self._calculate_risk_score(user_policies, high_risk_actions)
            
            if risk_score > 7:  # 임계값 설정
                risky_entities.append({
                    'Type': 'User',
                    'Name': user['UserName'],
                    'RiskScore': risk_score,
                    'Policies': user_policies
                })
        
        return risky_entities
    
    def detect_unused_credentials(self, days=90):
        """사용하지 않는 자격 증명 탐지"""
        unused_credentials = []
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        users = self.iam.list_users()['Users']
        for user in users:
            # 마지막 활동 시간 확인
            try:
                user_detail = self.iam.get_user(UserName=user['UserName'])
                last_used = user_detail.get('User', {}).get('PasswordLastUsed')
                
                if last_used and last_used < cutoff_date:
                    # 액세스 키 사용 이력 확인
                    access_keys = self.iam.list_access_keys(
                        UserName=user['UserName']
                    )['AccessKeyMetadata']
                    
                    for key in access_keys:
                        key_last_used = self.iam.get_access_key_last_used(
                            AccessKeyId=key['AccessKeyId']
                        )
                        
                        if (not key_last_used.get('AccessKeyLastUsed') or 
                            key_last_used['AccessKeyLastUsed']['LastUsedDate'] < cutoff_date):
                            
                            unused_credentials.append({
                                'UserName': user['UserName'],
                                'AccessKeyId': key['AccessKeyId'],
                                'LastUsed': key_last_used.get('AccessKeyLastUsed', {}).get('LastUsedDate'),
                                'Recommendation': 'Delete unused access key'
                            })
            
            except Exception as e:
                print(f"Error checking user {user['UserName']}: {e}")
        
        return unused_credentials
    
    def _get_user_policies(self, username):
        """사용자의 모든 정책 수집"""
        policies = []
        
        # 인라인 정책
        inline_policies = self.iam.list_user_policies(UserName=username)
        for policy_name in inline_policies['PolicyNames']:
            policy = self.iam.get_user_policy(
                UserName=username,
                PolicyName=policy_name
            )
            policies.append(policy['PolicyDocument'])
        
        # 연결된 관리형 정책
        attached_policies = self.iam.list_attached_user_policies(UserName=username)
        for policy in attached_policies['AttachedPolicies']:
            policy_version = self.iam.get_policy(PolicyArn=policy['PolicyArn'])
            policy_document = self.iam.get_policy_version(
                PolicyArn=policy['PolicyArn'],
                VersionId=policy_version['Policy']['DefaultVersionId']
            )
            policies.append(policy_document['PolicyVersion']['Document'])
        
        return policies
    
    def _calculate_risk_score(self, policies, high_risk_actions):
        """정책 기반 위험 점수 계산"""
        risk_score = 0
        
        for policy in policies:
            for statement in policy.get('Statement', []):
                if statement.get('Effect') == 'Allow':
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    for action in actions:
                        if action in high_risk_actions:
                            risk_score += 3
                        elif '*' in action:
                            risk_score += 2
                        elif any(risk_action.startswith(action.split(':')[0]) for risk_action in high_risk_actions):
                            risk_score += 1
        
        return risk_score

# 사용 예시
auditor = IAMSecurityAuditor()
risky_entities = auditor.audit_excessive_permissions()
unused_creds = auditor.detect_unused_credentials()
```

### 2. 네트워크 보안 강화

#### VPC 보안 그룹 최적화
```python
import boto3

class VPCSecurityAuditor:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
    
    def audit_security_groups(self):
        """보안 그룹 규칙 감사"""
        security_groups = self.ec2.describe_security_groups()['SecurityGroups']
        violations = []
        
        for sg in security_groups:
            # 인바운드 규칙 검사
            for rule in sg.get('IpPermissions', []):
                # 0.0.0.0/0 접근 허용 검사
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == '0.0.0.0/0':
                        severity = self._determine_severity(rule)
                        violations.append({
                            'SecurityGroupId': sg['GroupId'],
                            'Violation': 'Open to internet (0.0.0.0/0)',
                            'Protocol': rule.get('IpProtocol'),
                            'Port': f"{rule.get('FromPort', 'All')}-{rule.get('ToPort', 'All')}",
                            'Severity': severity,
                            'Recommendation': self._get_recommendation(rule, severity)
                        })
            
            # 아웃바운드 규칙 검사 (필요시)
            for rule in sg.get('IpPermissionsEgress', []):
                if (rule.get('IpRanges') and 
                    any(ip.get('CidrIp') == '0.0.0.0/0' for ip in rule['IpRanges']) and
                    rule.get('IpProtocol') == '-1'):  # 모든 트래픽
                    
                    violations.append({
                        'SecurityGroupId': sg['GroupId'],
                        'Violation': 'Unrestricted outbound traffic',
                        'Severity': 'Medium',
                        'Recommendation': 'Restrict outbound traffic to necessary destinations'
                    })
        
        return violations
    
    def _determine_severity(self, rule):
        """위험도 결정"""
        high_risk_ports = [22, 3389, 1433, 3306, 5432, 6379, 27017]
        port = rule.get('FromPort')
        
        if port in high_risk_ports:
            return 'Critical'
        elif port in range(80, 90) or port in range(443, 444):
            return 'Medium'
        else:
            return 'High'
    
    def _get_recommendation(self, rule, severity):
        """권장사항 제공"""
        if severity == 'Critical':
            return 'Immediately restrict access to specific IP ranges'
        elif severity == 'High':
            return 'Consider using ALB/NLB instead of direct exposure'
        else:
            return 'Review if internet access is necessary'

# 사용 예시
vpc_auditor = VPCSecurityAuditor()
sg_violations = vpc_auditor.audit_security_groups()
```

### 3. 데이터 보호 및 암호화

#### S3 보안 설정 자동화
```python
import boto3

class S3SecurityManager:
    def __init__(self):
        self.s3 = boto3.client('s3')
    
    def secure_bucket(self, bucket_name):
        """S3 버킷 보안 설정 자동화"""
        
        # 1. 퍼블릭 액세스 차단
        self.s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        
        # 2. 기본 암호화 설정
        self.s3.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        )
        
        # 3. 버전 관리 활성화
        self.s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # 4. 로깅 활성화
        self.s3.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                'LoggingEnabled': {
                    'TargetBucket': f'{bucket_name}-access-logs',
                    'TargetPrefix': 'access-logs/'
                }
            }
        )
        
        # 5. 보안 정책 적용
        security_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyInsecureConnections",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ],
                    "Condition": {
                        "Bool": {
                            "aws:SecureTransport": "false"
                        }
                    }
                },
                {
                    "Sid": "RequireSSEKMS",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:PutObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "StringNotEquals": {
                            "s3:x-amz-server-side-encryption": "aws:kms"
                        }
                    }
                }
            ]
        }
        
        self.s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(security_policy)
        )
        
        return {
            'bucket': bucket_name,
            'security_applied': [
                'Public access blocked',
                'Encryption enabled',
                'Versioning enabled',
                'Access logging enabled',
                'Security policy applied'
            ]
        }

# 사용 예시
s3_security = S3SecurityManager()
result = s3_security.secure_bucket('my-production-bucket')
```

## 🔍 지속적 모니터링 및 위협 탐지

### 1. CloudTrail 고급 분석

#### 의심스러운 활동 탐지
```python
import boto3
import json
from datetime import datetime, timedelta
from collections import defaultdict

class CloudTrailAnalyzer:
    def __init__(self):
        self.cloudtrail = boto3.client('cloudtrail')
        self.logs = boto3.client('logs')
    
    def detect_suspicious_activities(self, hours=24):
        """의심스러운 활동 패턴 탐지"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # CloudTrail 이벤트 조회
        events = self.cloudtrail.lookup_events(
            StartTime=start_time,
            EndTime=end_time,
            MaxItems=1000
        )
        
        suspicious_activities = []
        user_activity_count = defaultdict(int)
        failed_logins = defaultdict(int)
        privilege_escalations = []
        
        for event in events['Events']:
            event_name = event.get('EventName')
            username = event.get('Username', 'Unknown')
            source_ip = event.get('SourceIPAddress', 'Unknown')
            
            user_activity_count[username] += 1
            
            # 실패한 로그인 시도 감지
            if event_name in ['ConsoleLogin'] and 'Failed' in str(event.get('CloudTrailEvent', '')):
                failed_logins[source_ip] += 1
            
            # 권한 에스컬레이션 시도 감지
            if event_name in [
                'AttachUserPolicy', 'PutUserPolicy', 'CreateRole', 
                'AttachRolePolicy', 'PutRolePolicy', 'AssumeRole'
            ]:
                privilege_escalations.append({
                    'EventName': event_name,
                    'Username': username,
                    'SourceIP': source_ip,
                    'EventTime': event.get('EventTime'),
                    'Resources': event.get('Resources', [])
                })
            
            # 비정상적인 시간대 활동
            event_hour = event.get('EventTime').hour
            if event_hour < 6 or event_hour > 22:  # 업무 시간 외
                suspicious_activities.append({
                    'Type': 'Off-hours activity',
                    'EventName': event_name,
                    'Username': username,
                    'SourceIP': source_ip,
                    'EventTime': event.get('EventTime')
                })
        
        # 과도한 활동 감지
        for username, count in user_activity_count.items():
            if count > 100:  # 임계값
                suspicious_activities.append({
                    'Type': 'Excessive activity',
                    'Username': username,
                    'ActivityCount': count,
                    'Severity': 'High' if count > 500 else 'Medium'
                })
        
        # 무차별 대입 공격 감지
        for source_ip, failed_count in failed_logins.items():
            if failed_count > 10:
                suspicious_activities.append({
                    'Type': 'Brute force attack',
                    'SourceIP': source_ip,
                    'FailedAttempts': failed_count,
                    'Severity': 'Critical'
                })
        
        return {
            'suspicious_activities': suspicious_activities,
            'privilege_escalations': privilege_escalations,
            'summary': {
                'total_events': len(events['Events']),
                'unique_users': len(user_activity_count),
                'high_risk_activities': len([a for a in suspicious_activities if a.get('Severity') == 'Critical'])
            }
        }
    
    def analyze_api_usage_patterns(self):
        """API 사용 패턴 분석"""
        query = """
        fields @timestamp, eventName, sourceIPAddress, userIdentity.type, userIdentity.userName
        | filter eventName like /^(Create|Delete|Attach|Detach|Put|Get)/
        | stats count() by eventName, sourceIPAddress
        | sort count desc
        | limit 50
        """
        
        # CloudWatch Logs Insights 쿼리 실행
        response = self.logs.start_query(
            logGroupName='/aws/cloudtrail',
            startTime=int((datetime.utcnow() - timedelta(hours=24)).timestamp()),
            endTime=int(datetime.utcnow().timestamp()),
            queryString=query
        )
        
        return response['queryId']

# 사용 예시
analyzer = CloudTrailAnalyzer()
suspicious_report = analyzer.detect_suspicious_activities(24)
```

### 2. GuardDuty 자동 대응

#### 위협 탐지 시 자동 대응
```python
import boto3
import json

class GuardDutyAutoResponse:
    def __init__(self):
        self.guardduty = boto3.client('guardduty')
        self.ec2 = boto3.client('ec2')
        self.iam = boto3.client('iam')
        self.sns = boto3.client('sns')
    
    def lambda_handler(self, event, context):
        """GuardDuty 탐지 시 자동 대응 Lambda 함수"""
        
        # GuardDuty 이벤트 파싱
        detail = event['detail']
        finding_type = detail['type']
        severity = detail['severity']
        resource = detail.get('resource', {})
        
        response_actions = []
        
        # 높은 심각도의 위협에 대한 즉시 대응
        if severity >= 7.0:
            if 'UnauthorizedAPICall' in finding_type:
                response_actions.extend(
                    self._handle_unauthorized_api_call(detail)
                )
            elif 'Backdoor' in finding_type:
                response_actions.extend(
                    self._handle_backdoor_detection(detail)
                )
            elif 'CryptoCurrency' in finding_type:
                response_actions.extend(
                    self._handle_crypto_mining(detail)
                )
        
        # 알림 발송
        self._send_alert(detail, response_actions)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'finding_id': detail['id'],
                'actions_taken': response_actions
            })
        }
    
    def _handle_unauthorized_api_call(self, detail):
        """무단 API 호출 대응"""
        actions = []
        
        # 의심스러운 액세스 키 비활성화
        if 'accessKeyDetails' in detail['resource']:
            access_key_id = detail['resource']['accessKeyDetails']['accessKeyId']
            username = detail['resource']['accessKeyDetails']['userName']
            
            try:
                # 액세스 키 비활성화
                self.iam.update_access_key(
                    UserName=username,
                    AccessKeyId=access_key_id,
                    Status='Inactive'
                )
                actions.append(f"Deactivated access key: {access_key_id}")
                
                # 사용자 정책 제거 (임시)
                attached_policies = self.iam.list_attached_user_policies(
                    UserName=username
                )
                for policy in attached_policies['AttachedPolicies']:
                    self.iam.detach_user_policy(
                        UserName=username,
                        PolicyArn=policy['PolicyArn']
                    )
                actions.append(f"Removed policies from user: {username}")
                
            except Exception as e:
                actions.append(f"Failed to secure user {username}: {str(e)}")
        
        return actions
    
    def _handle_crypto_mining(self, detail):
        """암호화폐 마이닝 탐지 시 대응"""
        actions = []
        
        if 'instanceDetails' in detail['resource']:
            instance_id = detail['resource']['instanceDetails']['instanceId']
            
            try:
                # 인스턴스 격리 (보안 그룹 변경)
                isolation_sg = self._create_isolation_security_group()
                
                self.ec2.modify_instance_attribute(
                    InstanceId=instance_id,
                    Groups=[isolation_sg]
                )
                actions.append(f"Isolated instance: {instance_id}")
                
                # 스냅샷 생성 (포렌식 분석용)
                volumes = self.ec2.describe_instances(
                    InstanceIds=[instance_id]
                )['Reservations'][0]['Instances'][0]['BlockDeviceMappings']
                
                for volume in volumes:
                    volume_id = volume['Ebs']['VolumeId']
                    snapshot = self.ec2.create_snapshot(
                        VolumeId=volume_id,
                        Description=f"Forensic snapshot for incident: {detail['id']}"
                    )
                    actions.append(f"Created forensic snapshot: {snapshot['SnapshotId']}")
                
            except Exception as e:
                actions.append(f"Failed to contain instance {instance_id}: {str(e)}")
        
        return actions
    
    def _create_isolation_security_group(self):
        """격리용 보안 그룹 생성"""
        try:
            # 기존 격리 SG 확인
            response = self.ec2.describe_security_groups(
                Filters=[
                    {'Name': 'group-name', 'Values': ['incident-isolation-sg']}
                ]
            )
            
            if response['SecurityGroups']:
                return response['SecurityGroups'][0]['GroupId']
            
            # 새 격리 SG 생성
            sg = self.ec2.create_security_group(
                GroupName='incident-isolation-sg',
                Description='Security group for isolating compromised instances',
                VpcId=self._get_default_vpc_id()
            )
            
            # 모든 인바운드/아웃바운드 트래픽 차단
            self.ec2.revoke_security_group_egress(
                GroupId=sg['GroupId'],
                IpPermissions=[
                    {
                        'IpProtocol': '-1',
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            
            return sg['GroupId']
            
        except Exception as e:
            print(f"Failed to create isolation security group: {e}")
            return None
    
    def _get_default_vpc_id(self):
        """기본 VPC ID 조회"""
        vpcs = self.ec2.describe_vpcs(
            Filters=[{'Name': 'isDefault', 'Values': ['true']}]
        )
        return vpcs['Vpcs'][0]['VpcId'] if vpcs['Vpcs'] else None
    
    def _send_alert(self, detail, actions):
        """보안팀에 알림 발송"""
        message = {
            'Alert': 'GuardDuty Security Finding',
            'FindingId': detail['id'],
            'Type': detail['type'],
            'Severity': detail['severity'],
            'Description': detail['description'],
            'Actions': actions,
            'Timestamp': detail['updatedAt']
        }
        
        self.sns.publish(
            TopicArn='arn:aws:sns:region:account:security-alerts',
            Subject=f"🚨 Security Alert: {detail['type']}",
            Message=json.dumps(message, indent=2, default=str)
        )

# Lambda 함수로 배포
auto_response = GuardDutyAutoResponse()
```

## 🚨 보안 사고 대응 플레이북

### 1. 사고 분류 및 초기 대응

#### 사고 심각도 분류
```python
class IncidentClassifier:
    def __init__(self):
        self.severity_matrix = {
            'data_breach': {
                'pii_exposed': 'Critical',
                'financial_data': 'Critical',
                'internal_data': 'High',
                'public_data': 'Medium'
            },
            'unauthorized_access': {
                'admin_account': 'Critical',
                'production_system': 'High',
                'development_system': 'Medium',
                'test_system': 'Low'
            },
            'service_disruption': {
                'complete_outage': 'Critical',
                'partial_outage': 'High',
                'performance_degradation': 'Medium'
            }
        }
    
    def classify_incident(self, incident_type, sub_type, affected_systems=None):
        """사고 분류 및 심각도 결정"""
        base_severity = self.severity_matrix.get(incident_type, {}).get(sub_type, 'Medium')
        
        # 영향받은 시스템 수에 따른 조정
        if affected_systems:
            if len(affected_systems) > 10:
                base_severity = self._escalate_severity(base_severity)
        
        response_time = self._get_response_time(base_severity)
        escalation_path = self._get_escalation_path(base_severity)
        
        return {
            'severity': base_severity,
            'response_time': response_time,
            'escalation_path': escalation_path,
            'initial_actions': self._get_initial_actions(incident_type, base_severity)
        }
    
    def _escalate_severity(self, current_severity):
        """심각도 단계 상승"""
        escalation_map = {
            'Low': 'Medium',
            'Medium': 'High',
            'High': 'Critical',
            'Critical': 'Critical'
        }
        return escalation_map.get(current_severity, current_severity)
    
    def _get_response_time(self, severity):
        """심각도별 대응 시간"""
        response_times = {
            'Critical': '15 minutes',
            'High': '1 hour',
            'Medium': '4 hours',
            'Low': '24 hours'
        }
        return response_times.get(severity, '24 hours')
    
    def _get_escalation_path(self, severity):
        """에스컬레이션 경로"""
        if severity == 'Critical':
            return ['Security Team', 'CISO', 'CTO', 'CEO', 'Legal Team']
        elif severity == 'High':
            return ['Security Team', 'CISO', 'CTO']
        elif severity == 'Medium':
            return ['Security Team', 'CISO']
        else:
            return ['Security Team']
    
    def _get_initial_actions(self, incident_type, severity):
        """초기 대응 액션"""
        actions = {
            'data_breach': [
                'Identify affected data sets',
                'Contain the breach',
                'Assess legal notification requirements',
                'Document evidence'
            ],
            'unauthorized_access': [
                'Disable compromised accounts',
                'Change affected credentials',
                'Review access logs',
                'Implement additional monitoring'
            ],
            'service_disruption': [
                'Activate incident response team',
                'Assess service impact',
                'Implement workarounds',
                'Communicate with stakeholders'
            ]
        }
        
        base_actions = actions.get(incident_type, [])
        
        if severity in ['Critical', 'High']:
            base_actions.extend([
                'Notify senior leadership',
                'Consider external expertise',
                'Prepare legal consultation'
            ])
        
        return base_actions

# 사용 예시
classifier = IncidentClassifier()
incident_plan = classifier.classify_incident(
    'unauthorized_access', 
    'admin_account',
    affected_systems=['prod-web-01', 'prod-db-01', 'prod-api-01']
)
```

### 2. 자동화된 사고 대응 워크플로우

#### Step Functions 기반 사고 대응
```json
{
  "Comment": "Automated Security Incident Response Workflow",
  "StartAt": "ClassifyIncident",
  "States": {
    "ClassifyIncident": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:ClassifyIncident",
      "Next": "DecideResponse"
    },
    "DecideResponse": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.severity",
          "StringEquals": "Critical",
          "Next": "CriticalResponse"
        },
        {
          "Variable": "$.severity",
          "StringEquals": "High",
          "Next": "HighResponse"
        },
        {
          "Variable": "$.severity",
          "StringEquals": "Medium",
          "Next": "MediumResponse"
        }
      ],
      "Default": "LowResponse"
    },
    "CriticalResponse": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "IsolateResources",
          "States": {
            "IsolateResources": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:IsolateResources",
              "End": true
            }
          }
        },
        {
          "StartAt": "NotifyLeadership",
          "States": {
            "NotifyLeadership": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:NotifyLeadership",
              "End": true
            }
          }
        },
        {
          "StartAt": "CollectForensics",
          "States": {
            "CollectForensics": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:CollectForensics",
              "End": true
            }
          }
        }
      ],
      "Next": "DocumentIncident"
    },
    "HighResponse": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "SecureAccounts",
          "States": {
            "SecureAccounts": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:SecureAccounts",
              "End": true
            }
          }
        },
        {
          "StartAt": "NotifySecurityTeam",
          "States": {
            "NotifySecurityTeam": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:NotifySecurityTeam",
              "End": true
            }
          }
        }
      ],
      "Next": "DocumentIncident"
    },
    "MediumResponse": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:StandardResponse",
      "Next": "DocumentIncident"
    },
    "LowResponse": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:LogAndMonitor",
      "Next": "DocumentIncident"
    },
    "DocumentIncident": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:DocumentIncident",
      "Next": "GenerateReport"
    },
    "GenerateReport": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:GenerateReport",
      "End": true
    }
  }
}
```

## 📋 보안 체크리스트 및 모범 사례

### 일일 보안 체크리스트
```markdown
## 🔒 일일 보안 점검 체크리스트

### IAM 및 액세스 관리
- [ ] 새로운 사용자 계정 생성 검토
- [ ] 권한 변경 사항 확인
- [ ] 90일 이상 미사용 계정 확인
- [ ] 다중 인증(MFA) 활성화 상태 점검

### 네트워크 보안
- [ ] 보안 그룹 변경 사항 검토
- [ ] VPC Flow Logs 이상 트래픽 확인
- [ ] 신규 공개 IP 할당 검토
- [ ] 비정상적인 데이터 전송량 확인

### 데이터 보호
- [ ] S3 버킷 퍼블릭 액세스 설정 확인
- [ ] 암호화되지 않은 새 리소스 탐지
- [ ] 백업 상태 및 무결성 확인
- [ ] 데이터 분류 정책 준수 확인

### 모니터링 및 로깅
- [ ] CloudTrail 로그 수집 상태 확인
- [ ] GuardDuty 탐지 결과 검토
- [ ] Config 규칙 준수 상태 확인
- [ ] Security Hub 보안 점수 검토

### 취약성 관리
- [ ] EC2 인스턴스 패치 상태 확인
- [ ] 컨테이너 이미지 스캔 결과 검토
- [ ] 써드파티 라이브러리 취약성 확인
- [ ] SSL/TLS 인증서 만료 예정 확인
```

### 주간 보안 리뷰
```python
class WeeklySecurityReview:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.s3 = boto3.client('s3')
        self.iam = boto3.client('iam')
        self.config = boto3.client('config')
    
    def generate_weekly_report(self):
        """주간 보안 리포트 생성"""
        report = {
            'period': f"{datetime.now() - timedelta(days=7)} to {datetime.now()}",
            'iam_review': self._review_iam_changes(),
            'network_review': self._review_network_changes(),
            'resource_review': self._review_resource_changes(),
            'compliance_status': self._check_compliance_status(),
            'recommendations': []
        }
        
        # 권장사항 생성
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _review_iam_changes(self):
        """IAM 변경사항 검토"""
        # CloudTrail 이벤트에서 IAM 변경사항 추출
        iam_events = [
            'CreateUser', 'DeleteUser', 'AttachUserPolicy', 
            'DetachUserPolicy', 'CreateRole', 'DeleteRole'
        ]
        
        # 구현 로직...
        return {
            'new_users': 3,
            'deleted_users': 1,
            'policy_changes': 5,
            'role_changes': 2
        }
    
    def _generate_recommendations(self, report):
        """보안 권장사항 생성"""
        recommendations = []
        
        if report['iam_review']['new_users'] > 5:
            recommendations.append({
                'priority': 'High',
                'category': 'IAM',
                'issue': 'High number of new users created',
                'recommendation': 'Review user access patterns and consider using federated identity'
            })
        
        if report['compliance_status']['non_compliant_resources'] > 10:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Compliance',
                'issue': 'Multiple non-compliant resources detected',
                'recommendation': 'Implement automated remediation for common compliance issues'
            })
        
        return recommendations

# 사용 예시
weekly_review = WeeklySecurityReview()
security_report = weekly_review.generate_weekly_report()
```

## 💭 마무리

AWS 환경에서의 보안은 지속적인 프로세스입니다. 이번 포스트에서 다룬 내용들을 요약하면:

### 🎯 핵심 보안 원칙
1. **심층 방어**: 다층 보안 체계 구축
2. **최소 권한**: 필요한 최소한의 권한만 부여
3. **지속적 모니터링**: 실시간 위협 탐지 및 대응
4. **자동화**: 수동 오류 최소화를 위한 자동화 구현
5. **준비와 대응**: 체계적인 사고 대응 계획 수립

### 🚀 실행 우선순위
1. **즉시 구현**: IAM MFA, 보안 그룹 점검, CloudTrail 활성화
2. **단기 구현**: GuardDuty 설정, 자동화된 보안 검사
3. **장기 구현**: 포괄적인 사고 대응 체계, 보안 문화 정착

보안은 기술적 해결책뿐만 아니라 조직 문화와 프로세스의 변화도 필요합니다. 정기적인 교육과 훈련을 통해 전체 조직의 보안 인식을 높이는 것도 중요합니다.

---

**관련 포스트**:
- [AWS SAA 실전 문제 풀이 - VPC 보안과 네트워크 ACL]({% post_url 2025-06-23-aws-saa-security-vpc-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - Well-Architected Framework와 비용 최적화]({% post_url 2025-06-30-aws-saa-well-architected-cost-optimization %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})

**태그**: #AWS #Security #IAM #CloudTrail #GuardDuty #IncidentResponse #보안 #사고대응 #모범사례
