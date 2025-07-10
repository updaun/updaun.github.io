---
layout: post
title: "AWS SAA 실습 문제: CloudFormation과 CDK를 활용한 Infrastructure as Code 설계"
categories: [aws-saa]
tags: [aws, cloudformation, cdk, infrastructure-as-code, devops, automation, ci-cd]
date: 2025-07-10
---

## 📋 문제 시나리오

당신은 금융 서비스 회사의 클라우드 엔지니어로 근무하고 있습니다. 회사에서는 수동으로 관리되던 AWS 인프라를 Infrastructure as Code(IaC)로 전환하여 일관성, 재현성, 그리고 규정 준수를 보장하려고 합니다. 개발, 스테이징, 프로덕션 환경을 자동화된 방식으로 구축하고 관리해야 합니다.

### 비즈니스 요구사항

**현재 상황:**
- **수동 인프라 관리**: 콘솔을 통한 수동 리소스 생성 및 관리
- **환경 불일치**: 개발, 스테이징, 프로덕션 환경 간 차이점 존재
- **규정 준수**: 금융 업계 보안 요구사항 및 감사 추적 필요
- **확장성**: 새로운 서비스 출시 시 빠른 인프라 프로비저닝 필요

**목표:**
1. **일관성 있는 환경 구성**: 모든 환경에서 동일한 구성 보장
2. **버전 관리**: 인프라 변경 사항 추적 및 롤백 가능
3. **자동화된 배포**: CI/CD 파이프라인을 통한 인프라 배포
4. **비용 최적화**: 리소스 사용 최적화 및 비용 모니터링
5. **보안 강화**: 보안 모범 사례 및 규정 준수 자동화

### 기술적 제약사항
- **멀티 리전 지원**: 재해 복구를 위한 다중 지역 배포
- **환경 격리**: 개발, 스테이징, 프로덕션 환경 분리
- **네트워크 보안**: VPC, 서브넷, 보안 그룹 세밀한 제어
- **모니터링**: 인프라 상태 실시간 모니터링
- **백업 및 복구**: 자동화된 백업 및 복구 전략

## 🎯 해결 방안

### 1. 전체 아키텍처 설계

```
[Git Repository] → [CodePipeline] → [CloudFormation/CDK] → [Multi-Environment AWS]
        ↓                ↓                    ↓
[Version Control] → [CI/CD Pipeline] → [Infrastructure Deployment]
        ↓                ↓                    ↓
[Branch Strategy] → [Testing/Validation] → [Environment Management]
```

### 2. 브랜치 전략 및 환경 관리

#### A. Git 브랜치 전략
```yaml
Branch Strategy:
  main:
    - Production 환경 배포
    - 모든 변경사항 리뷰 필수
    - 태그를 통한 릴리스 관리
    
  develop:
    - Development 환경 배포
    - 기능 개발 및 통합
    - 자동 테스트 실행
    
  staging:
    - Staging 환경 배포
    - 프로덕션 배포 전 최종 검증
    - 성능 및 부하 테스트
    
  feature/*:
    - 기능별 브랜치
    - 개발자 개인 환경 배포
    - Pull Request 를 통한 코드 리뷰
```

#### B. 환경별 파라미터 관리
```yaml
# parameters/dev.yaml
Parameters:
  Environment: dev
  VpcCidr: 10.0.0.0/16
  InstanceType: t3.micro
  MinSize: 1
  MaxSize: 3
  DesiredCapacity: 1
  DatabaseInstanceType: db.t3.micro
  DatabaseMultiAZ: false
  
# parameters/staging.yaml  
Parameters:
  Environment: staging
  VpcCidr: 10.1.0.0/16
  InstanceType: t3.small
  MinSize: 2
  MaxSize: 6
  DesiredCapacity: 2
  DatabaseInstanceType: db.t3.small
  DatabaseMultiAZ: true
  
# parameters/prod.yaml
Parameters:
  Environment: prod
  VpcCidr: 10.2.0.0/16
  InstanceType: m5.large
  MinSize: 3
  MaxSize: 12
  DesiredCapacity: 3
  DatabaseInstanceType: db.r5.large
  DatabaseMultiAZ: true
```

### 3. CloudFormation 템플릿 구조

#### A. 네트워크 스택 (network.yaml)
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Network infrastructure for financial services application'

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    
  VpcCidr:
    Type: String
    Default: 10.0.0.0/16
    Description: CIDR block for VPC
    
  AvailabilityZones:
    Type: CommaDelimitedList
    Default: "us-east-1a,us-east-1b,us-east-1c"
    Description: List of Availability Zones

Resources:
  # VPC
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCidr
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-vpc"
        - Key: Environment
          Value: !Ref Environment

  # Internet Gateway
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-igw"
        - Key: Environment
          Value: !Ref Environment

  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      InternetGatewayId: !Ref InternetGateway
      VpcId: !Ref VPC

  # Public Subnets
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !Ref AvailabilityZones]
      CidrBlock: !Select [0, !Cidr [!Ref VpcCidr, 12, 8]]
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-subnet-1"
        - Key: Environment
          Value: !Ref Environment

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [1, !Ref AvailabilityZones]
      CidrBlock: !Select [1, !Cidr [!Ref VpcCidr, 12, 8]]
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-subnet-2"

  # Private Subnets
  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !Ref AvailabilityZones]
      CidrBlock: !Select [2, !Cidr [!Ref VpcCidr, 12, 8]]
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-private-subnet-1"

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [1, !Ref AvailabilityZones]
      CidrBlock: !Select [3, !Cidr [!Ref VpcCidr, 12, 8]]
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-private-subnet-2"

  # Database Subnets
  DatabaseSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !Ref AvailabilityZones]
      CidrBlock: !Select [4, !Cidr [!Ref VpcCidr, 12, 8]]
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-database-subnet-1"

  DatabaseSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [1, !Ref AvailabilityZones]
      CidrBlock: !Select [5, !Cidr [!Ref VpcCidr, 12, 8]]
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-database-subnet-2"

  # NAT Gateways
  NatGateway1EIP:
    Type: AWS::EC2::EIP
    DependsOn: InternetGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway1:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGateway1EIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-natgw-1"

  # Route Tables
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-rt"

  DefaultPublicRoute:
    Type: AWS::EC2::Route
    DependsOn: InternetGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PublicRouteTable
      SubnetId: !Ref PublicSubnet1

  PublicSubnet2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PublicRouteTable
      SubnetId: !Ref PublicSubnet2

  PrivateRouteTable1:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-private-rt-1"

  DefaultPrivateRoute1:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable1
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway1

  PrivateSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PrivateRouteTable1
      SubnetId: !Ref PrivateSubnet1

Outputs:
  VPC:
    Description: A reference to the created VPC
    Value: !Ref VPC
    Export:
      Name: !Sub "${Environment}-VPC"

  PublicSubnets:
    Description: A list of the public subnets
    Value: !Join [",", [!Ref PublicSubnet1, !Ref PublicSubnet2]]
    Export:
      Name: !Sub "${Environment}-PublicSubnets"

  PrivateSubnets:
    Description: A list of the private subnets
    Value: !Join [",", [!Ref PrivateSubnet1, !Ref PrivateSubnet2]]
    Export:
      Name: !Sub "${Environment}-PrivateSubnets"

  DatabaseSubnets:
    Description: A list of the database subnets
    Value: !Join [",", [!Ref DatabaseSubnet1, !Ref DatabaseSubnet2]]
    Export:
      Name: !Sub "${Environment}-DatabaseSubnets"
```

#### B. 보안 스택 (security.yaml)
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Security groups and IAM roles for financial services application'

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]

Resources:
  # Application Load Balancer Security Group
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for Application Load Balancer
      VpcId: !ImportValue 
        Fn::Sub: "${Environment}-VPC"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
          Description: HTTP from anywhere
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
          Description: HTTPS from anywhere
      SecurityGroupEgress:
        - IpProtocol: -1
          CidrIp: 0.0.0.0/0
          Description: All outbound traffic
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-alb-sg"
        - Key: Environment
          Value: !Ref Environment

  # Application Security Group
  ApplicationSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for application servers
      VpcId: !ImportValue 
        Fn::Sub: "${Environment}-VPC"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          SourceSecurityGroupId: !Ref ALBSecurityGroup
          Description: HTTP from ALB
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          SourceSecurityGroupId: !Ref BastionSecurityGroup
          Description: SSH from bastion
      SecurityGroupEgress:
        - IpProtocol: -1
          CidrIp: 0.0.0.0/0
          Description: All outbound traffic
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-app-sg"

  # Database Security Group
  DatabaseSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for database
      VpcId: !ImportValue 
        Fn::Sub: "${Environment}-VPC"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 3306
          ToPort: 3306
          SourceSecurityGroupId: !Ref ApplicationSecurityGroup
          Description: MySQL from application
        - IpProtocol: tcp
          FromPort: 3306
          ToPort: 3306
          SourceSecurityGroupId: !Ref BastionSecurityGroup
          Description: MySQL from bastion
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-db-sg"

  # Bastion Security Group
  BastionSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for bastion host
      VpcId: !ImportValue 
        Fn::Sub: "${Environment}-VPC"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 10.0.0.0/8
          Description: SSH from corporate network
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-bastion-sg"

  # IAM Role for EC2 instances
  EC2InstanceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${Environment}-ec2-instance-role"
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub "arn:aws:s3:::${Environment}-app-bucket/*"
        - PolicyName: SecretsManagerAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource: !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Environment}/database/*"

  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      InstanceProfileName: !Sub "${Environment}-ec2-instance-profile"
      Roles:
        - !Ref EC2InstanceRole

Outputs:
  ALBSecurityGroup:
    Description: Security group for ALB
    Value: !Ref ALBSecurityGroup
    Export:
      Name: !Sub "${Environment}-ALB-SG"

  ApplicationSecurityGroup:
    Description: Security group for application
    Value: !Ref ApplicationSecurityGroup
    Export:
      Name: !Sub "${Environment}-App-SG"

  DatabaseSecurityGroup:
    Description: Security group for database
    Value: !Ref DatabaseSecurityGroup
    Export:
      Name: !Sub "${Environment}-DB-SG"

  EC2InstanceProfile:
    Description: IAM instance profile for EC2
    Value: !Ref EC2InstanceProfile
    Export:
      Name: !Sub "${Environment}-EC2-InstanceProfile"
```

### 4. AWS CDK 구현 예제

#### A. CDK 스택 구조
```typescript
// lib/financial-services-stack.ts
import * as cdk from '@aws-cdk/core';
import * as ec2 from '@aws-cdk/aws-ec2';
import * as elbv2 from '@aws-cdk/aws-elasticloadbalancingv2';
import * as autoscaling from '@aws-cdk/aws-autoscaling';
import * as rds from '@aws-cdk/aws-rds';
import * as s3 from '@aws-cdk/aws-s3';
import * as iam from '@aws-cdk/aws-iam';
import * as cloudwatch from '@aws-cdk/aws-cloudwatch';

export interface FinancialServicesStackProps extends cdk.StackProps {
  environment: string;
  vpcCidr: string;
  instanceType: string;
  minSize: number;
  maxSize: number;
  desiredCapacity: number;
  databaseInstanceType: string;
  databaseMultiAZ: boolean;
}

export class FinancialServicesStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props: FinancialServicesStackProps) {
    super(scope, id, props);

    // VPC 생성
    const vpc = new ec2.Vpc(this, 'VPC', {
      cidr: props.vpcCidr,
      maxAzs: 3,
      natGateways: props.environment === 'prod' ? 3 : 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_NAT,
        },
        {
          cidrMask: 24,
          name: 'Database',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    // 보안 그룹 생성
    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc,
      description: 'Security group for Application Load Balancer',
      allowAllOutbound: true,
    });

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'HTTP from anywhere'
    );

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'HTTPS from anywhere'
    );

    const appSecurityGroup = new ec2.SecurityGroup(this, 'AppSecurityGroup', {
      vpc,
      description: 'Security group for application servers',
      allowAllOutbound: true,
    });

    appSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8080),
      'HTTP from ALB'
    );

    // IAM 역할 생성
    const ec2Role = new iam.Role(this, 'EC2Role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    // S3 버킷 생성
    const appBucket = new s3.Bucket(this, 'AppBucket', {
      bucketName: `${props.environment}-financial-app-bucket`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      publicReadAccess: false,
      removalPolicy: props.environment === 'prod' 
        ? cdk.RemovalPolicy.RETAIN 
        : cdk.RemovalPolicy.DESTROY,
    });

    // S3 버킷 접근 권한 추가
    appBucket.grantReadWrite(ec2Role);

    // Launch Template 생성
    const launchTemplate = new ec2.LaunchTemplate(this, 'LaunchTemplate', {
      instanceType: new ec2.InstanceType(props.instanceType),
      machineImage: ec2.MachineImage.latestAmazonLinux(),
      role: ec2Role,
      securityGroup: appSecurityGroup,
      userData: ec2.UserData.forLinux(),
    });

    // Auto Scaling Group 생성
    const asg = new autoscaling.AutoScalingGroup(this, 'ASG', {
      vpc,
      launchTemplate,
      minCapacity: props.minSize,
      maxCapacity: props.maxSize,
      desiredCapacity: props.desiredCapacity,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_NAT,
      },
      healthCheck: autoscaling.HealthCheck.elb({
        grace: cdk.Duration.minutes(5),
      }),
    });

    // Application Load Balancer 생성
    const alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
    });

    // Target Group 생성
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'TargetGroup', {
      port: 8080,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc,
      targets: [asg],
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
    });

    // Listener 생성
    const listener = alb.addListener('Listener', {
      port: 80,
      defaultTargetGroups: [targetGroup],
    });

    // RDS 서브넷 그룹 생성
    const dbSubnetGroup = new rds.SubnetGroup(this, 'DatabaseSubnetGroup', {
      vpc,
      description: 'Subnet group for RDS database',
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
    });

    // RDS 데이터베이스 생성
    const database = new rds.DatabaseInstance(this, 'Database', {
      engine: rds.DatabaseInstanceEngine.mysql({
        version: rds.MysqlEngineVersion.VER_8_0,
      }),
      instanceType: new ec2.InstanceType(props.databaseInstanceType),
      vpc,
      subnetGroup: dbSubnetGroup,
      multiAz: props.databaseMultiAZ,
      credentials: rds.Credentials.fromGeneratedSecret('admin'),
      backupRetention: cdk.Duration.days(7),
      deletionProtection: props.environment === 'prod',
      storageEncrypted: true,
    });

    // 데이터베이스 보안 그룹 설정
    database.connections.allowDefaultPortFrom(
      appSecurityGroup,
      'Access from application'
    );

    // CloudWatch 알람 설정
    const cpuAlarm = new cloudwatch.Alarm(this, 'CPUAlarm', {
      metric: asg.metricCpuUtilization(),
      threshold: 80,
      evaluationPeriods: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // 스케일링 정책 설정
    const scaleUpPolicy = asg.scaleOnMetric('ScaleUp', {
      metric: asg.metricCpuUtilization(),
      scalingSteps: [
        { upper: 70, change: +1 },
        { upper: 85, change: +2 },
        { upper: 100, change: +3 },
      ],
      adjustmentType: autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
    });

    const scaleDownPolicy = asg.scaleOnMetric('ScaleDown', {
      metric: asg.metricCpuUtilization(),
      scalingSteps: [
        { upper: 30, change: -1 },
        { upper: 50, change: 0 },
      ],
      adjustmentType: autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
    });

    // 출력 값 설정
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: alb.loadBalancerDnsName,
      description: 'DNS name of the load balancer',
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: database.instanceEndpoint.hostname,
      description: 'RDS database endpoint',
    });

    // 태그 추가
    cdk.Tags.of(this).add('Environment', props.environment);
    cdk.Tags.of(this).add('Project', 'FinancialServices');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');
  }
}
```

#### B. CDK 앱 진입점
```typescript
// bin/financial-services.ts
import * as cdk from '@aws-cdk/core';
import { FinancialServicesStack } from '../lib/financial-services-stack';

const app = new cdk.App();

// 환경별 설정
const environments = {
  dev: {
    environment: 'dev',
    vpcCidr: '10.0.0.0/16',
    instanceType: 't3.micro',
    minSize: 1,
    maxSize: 3,
    desiredCapacity: 1,
    databaseInstanceType: 'db.t3.micro',
    databaseMultiAZ: false,
  },
  staging: {
    environment: 'staging',
    vpcCidr: '10.1.0.0/16',
    instanceType: 't3.small',
    minSize: 2,
    maxSize: 6,
    desiredCapacity: 2,
    databaseInstanceType: 'db.t3.small',
    databaseMultiAZ: true,
  },
  prod: {
    environment: 'prod',
    vpcCidr: '10.2.0.0/16',
    instanceType: 'm5.large',
    minSize: 3,
    maxSize: 12,
    desiredCapacity: 3,
    databaseInstanceType: 'db.r5.large',
    databaseMultiAZ: true,
  },
};

// 환경별 스택 생성
Object.entries(environments).forEach(([env, config]) => {
  new FinancialServicesStack(app, `FinancialServices-${env}`, {
    ...config,
    env: {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: process.env.CDK_DEFAULT_REGION,
    },
  });
});
```

### 5. CI/CD 파이프라인 구현

#### A. CodePipeline 설정
```yaml
# pipeline/pipeline.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CI/CD Pipeline for Infrastructure as Code'

Parameters:
  GitHubOwner:
    Type: String
    Description: GitHub repository owner
    
  GitHubRepo:
    Type: String
    Description: GitHub repository name
    
  GitHubBranch:
    Type: String
    Default: main
    Description: GitHub branch name

Resources:
  # S3 Bucket for artifacts
  ArtifactBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${AWS::StackName}-artifacts-${AWS::AccountId}"
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  # CodePipeline Service Role
  CodePipelineServiceRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: codepipeline.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: CodePipelineServicePolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:GetBucketVersioning
                Resource:
                  - !Sub "${ArtifactBucket}/*"
                  - !GetAtt ArtifactBucket.Arn
              - Effect: Allow
                Action:
                  - codebuild:BatchGetBuilds
                  - codebuild:StartBuild
                Resource: "*"
              - Effect: Allow
                Action:
                  - cloudformation:CreateStack
                  - cloudformation:DescribeStacks
                  - cloudformation:DeleteStack
                  - cloudformation:UpdateStack
                  - cloudformation:CreateChangeSet
                  - cloudformation:ExecuteChangeSet
                  - cloudformation:DeleteChangeSet
                  - cloudformation:DescribeChangeSet
                  - cloudformation:SetStackPolicy
                  - cloudformation:ValidateTemplate
                Resource: "*"
              - Effect: Allow
                Action:
                  - iam:PassRole
                Resource: "*"

  # CodeBuild Project for Testing
  TestProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub "${AWS::StackName}-test"
      ServiceRole: !GetAtt CodeBuildServiceRole.Arn
      Artifacts:
        Type: CODEPIPELINE
      Environment:
        Type: LINUX_CONTAINER
        ComputeType: BUILD_GENERAL1_SMALL
        Image: aws/codebuild/standard:5.0
      Source:
        Type: CODEPIPELINE
        BuildSpec: |
          version: 0.2
          phases:
            install:
              runtime-versions:
                nodejs: 14
              commands:
                - npm install -g aws-cdk
                - pip install cfn-lint
                - pip install taskcat
            pre_build:
              commands:
                - echo Logging in to Amazon ECR...
                - aws --version
                - cfn-lint --version
            build:
              commands:
                - echo Build started on `date`
                - echo Testing CloudFormation templates...
                - cfn-lint templates/*.yaml
                - echo Testing CDK application...
                - cd cdk && npm install
                - npm run build
                - npm run test
                - cdk synth
            post_build:
              commands:
                - echo Build completed on `date`

  # CodeBuild Service Role
  CodeBuildServiceRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: codebuild.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: CodeBuildServicePolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: "*"
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub "${ArtifactBucket}/*"

  # CodePipeline
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: !Sub "${AWS::StackName}-pipeline"
      RoleArn: !GetAtt CodePipelineServiceRole.Arn
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactBucket
      Stages:
        - Name: Source
          Actions:
            - Name: SourceAction
              ActionTypeId:
                Category: Source
                Owner: ThirdParty
                Provider: GitHub
                Version: '1'
              Configuration:
                Owner: !Ref GitHubOwner
                Repo: !Ref GitHubRepo
                Branch: !Ref GitHubBranch
                OAuthToken: !Ref GitHubToken
              OutputArtifacts:
                - Name: SourceOutput
                
        - Name: Test
          Actions:
            - Name: TestAction
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              Configuration:
                ProjectName: !Ref TestProject
              InputArtifacts:
                - Name: SourceOutput
              OutputArtifacts:
                - Name: TestOutput
                
        - Name: Deploy-Dev
          Actions:
            - Name: DeployDev
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CloudFormation
                Version: '1'
              Configuration:
                ActionMode: CREATE_UPDATE
                StackName: financial-services-dev
                TemplatePath: TestOutput::templates/main.yaml
                TemplateConfiguration: TestOutput::parameters/dev.json
                Capabilities: CAPABILITY_IAM
                RoleArn: !GetAtt CloudFormationRole.Arn
              InputArtifacts:
                - Name: TestOutput
              Region: !Ref AWS::Region
              RunOrder: 1
```

#### B. GitHub Actions 워크플로우
```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure Deployment

on:
  push:
    branches: [main, develop, staging]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '16'
          
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          npm install -g aws-cdk
          pip install cfn-lint taskcat
          
      - name: Lint CloudFormation templates
        run: |
          cfn-lint templates/*.yaml
          
      - name: Test CDK application
        run: |
          cd cdk
          npm install
          npm run build
          npm run test
          cdk synth
          
      - name: Security scan
        run: |
          # Checkov 보안 스캔
          pip install checkov
          checkov -d templates/ --framework cloudformation
          
  deploy-dev:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: development
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: Deploy to Development
        run: |
          aws cloudformation deploy \
            --template-file templates/main.yaml \
            --stack-name financial-services-dev \
            --parameter-overrides file://parameters/dev.json \
            --capabilities CAPABILITY_IAM \
            --no-fail-on-empty-changeset
            
  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    environment: staging
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: Deploy to Staging
        run: |
          aws cloudformation deploy \
            --template-file templates/main.yaml \
            --stack-name financial-services-staging \
            --parameter-overrides file://parameters/staging.json \
            --capabilities CAPABILITY_IAM \
            --no-fail-on-empty-changeset
            
  deploy-prod:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: Deploy to Production
        run: |
          aws cloudformation deploy \
            --template-file templates/main.yaml \
            --stack-name financial-services-prod \
            --parameter-overrides file://parameters/prod.json \
            --capabilities CAPABILITY_IAM \
            --no-fail-on-empty-changeset
```

### 6. 모니터링 및 알림 구성

#### A. CloudWatch 대시보드
```yaml
# monitoring/dashboard.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch Dashboard for Infrastructure Monitoring'

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]

Resources:
  InfrastructureDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: !Sub "${Environment}-infrastructure-dashboard"
      DashboardBody: !Sub |
        {
          "widgets": [
            {
              "type": "metric",
              "x": 0,
              "y": 0,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "AWS/ApplicationELB", "RequestCount", "LoadBalancer", "${Environment}-alb" ],
                  [ ".", "TargetResponseTime", ".", "." ],
                  [ ".", "HTTPCode_Target_4XX_Count", ".", "." ],
                  [ ".", "HTTPCode_Target_5XX_Count", ".", "." ]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "${AWS::Region}",
                "title": "ALB Metrics"
              }
            },
            {
              "type": "metric",
              "x": 12,
              "y": 0,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "${Environment}-asg" ],
                  [ ".", "NetworkIn", ".", "." ],
                  [ ".", "NetworkOut", ".", "." ]
                ],
                "period": 300,
                "stat": "Average",
                "region": "${AWS::Region}",
                "title": "EC2 Metrics"
              }
            },
            {
              "type": "metric",
              "x": 0,
              "y": 6,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "${Environment}-database" ],
                  [ ".", "DatabaseConnections", ".", "." ],
                  [ ".", "ReadLatency", ".", "." ],
                  [ ".", "WriteLatency", ".", "." ]
                ],
                "period": 300,
                "stat": "Average",
                "region": "${AWS::Region}",
                "title": "RDS Metrics"
              }
            },
            {
              "type": "log",
              "x": 12,
              "y": 6,
              "width": 12,
              "height": 6,
              "properties": {
                "query": "SOURCE '/aws/lambda/financial-services-${Environment}' | fields @timestamp, @message | sort @timestamp desc | limit 20",
                "region": "${AWS::Region}",
                "title": "Recent Log Events"
              }
            }
          ]
        }

  # 알람 설정
  HighCPUAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "${Environment}-high-cpu-utilization"
      AlarmDescription: "Alarm when CPU exceeds 80%"
      MetricName: CPUUtilization
      Namespace: AWS/EC2
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: AutoScalingGroupName
          Value: !Sub "${Environment}-asg"
      AlarmActions:
        - !Ref SNSTopic

  DatabaseConnectionAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "${Environment}-database-connections"
      AlarmDescription: "Alarm when database connections exceed 80"
      MetricName: DatabaseConnections
      Namespace: AWS/RDS
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: DBInstanceIdentifier
          Value: !Sub "${Environment}-database"
      AlarmActions:
        - !Ref SNSTopic

  # SNS 토픽
  SNSTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub "${Environment}-infrastructure-alerts"
      DisplayName: !Sub "${Environment} Infrastructure Alerts"

  SNSSubscription:
    Type: AWS::SNS::Subscription
    Properties:
      Protocol: email
      TopicArn: !Ref SNSTopic
      Endpoint: !Sub "${Environment}-ops@company.com"
```

### 7. 보안 및 규정 준수

#### A. AWS Config 규칙
```yaml
# compliance/config-rules.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'AWS Config rules for compliance monitoring'

Resources:
  ConfigRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: config.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/ConfigRole
      Policies:
        - PolicyName: ConfigBucketPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetBucketAcl
                  - s3:ListBucket
                Resource: !GetAtt ConfigBucket.Arn
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub "${ConfigBucket}/*"

  ConfigBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "config-bucket-${AWS::AccountId}-${AWS::Region}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  ConfigurationRecorder:
    Type: AWS::Config::ConfigurationRecorder
    Properties:
      Name: default
      RoleARN: !GetAtt ConfigRole.Arn
      RecordingGroup:
        AllSupported: true
        IncludeGlobalResourceTypes: true

  DeliveryChannel:
    Type: AWS::Config::DeliveryChannel
    Properties:
      Name: default
      S3BucketName: !Ref ConfigBucket

  # 보안 그룹 규칙 - SSH 접근 제한
  SSHRestrictedRule:
    Type: AWS::Config::ConfigRule
    DependsOn: ConfigurationRecorder
    Properties:
      ConfigRuleName: ssh-restricted
      Description: Checks whether security groups allow unrestricted SSH access
      Source:
        Owner: AWS
        SourceIdentifier: INCOMING_SSH_DISABLED

  # RDS 암호화 규칙
  RDSEncryptionRule:
    Type: AWS::Config::ConfigRule
    DependsOn: ConfigurationRecorder
    Properties:
      ConfigRuleName: rds-storage-encrypted
      Description: Checks whether RDS instances are encrypted
      Source:
        Owner: AWS
        SourceIdentifier: RDS_STORAGE_ENCRYPTED

  # S3 버킷 공개 액세스 금지
  S3PublicAccessRule:
    Type: AWS::Config::ConfigRule
    DependsOn: ConfigurationRecorder
    Properties:
      ConfigRuleName: s3-bucket-public-access-prohibited
      Description: Checks that S3 buckets do not allow public access
      Source:
        Owner: AWS
        SourceIdentifier: S3_BUCKET_PUBLIC_ACCESS_PROHIBITED

  # ELB 로깅 활성화
  ELBLoggingRule:
    Type: AWS::Config::ConfigRule
    DependsOn: ConfigurationRecorder
    Properties:
      ConfigRuleName: elb-logging-enabled
      Description: Checks whether ELB has logging enabled
      Source:
        Owner: AWS
        SourceIdentifier: ELB_LOGGING_ENABLED
```

### 8. 재해 복구 및 백업 전략

#### A. 크로스 리전 백업
```yaml
# backup/cross-region-backup.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Cross-region backup and disaster recovery'

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    
  BackupRegion:
    Type: String
    Default: us-west-2
    Description: Region for backup storage

Resources:
  # Backup Vault
  BackupVault:
    Type: AWS::Backup::BackupVault
    Properties:
      BackupVaultName: !Sub "${Environment}-backup-vault"
      EncryptionKeyArn: !GetAtt BackupKey.Arn

  # KMS Key for Backup
  BackupKey:
    Type: AWS::KMS::Key
    Properties:
      Description: KMS key for backup encryption
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: Enable IAM User Permissions
            Effect: Allow
            Principal:
              AWS: !Sub "arn:aws:iam::${AWS::AccountId}:root"
            Action: "kms:*"
            Resource: "*"
          - Sid: Allow AWS Backup
            Effect: Allow
            Principal:
              Service: backup.amazonaws.com
            Action:
              - kms:Decrypt
              - kms:GenerateDataKey
            Resource: "*"

  BackupKeyAlias:
    Type: AWS::KMS::Alias
    Properties:
      AliasName: !Sub "alias/${Environment}-backup-key"
      TargetKeyId: !Ref BackupKey

  # Backup Plan
  BackupPlan:
    Type: AWS::Backup::BackupPlan
    Properties:
      BackupPlan:
        BackupPlanName: !Sub "${Environment}-backup-plan"
        BackupPlanRule:
          - RuleName: DailyBackup
            TargetBackupVault: !Ref BackupVault
            ScheduleExpression: "cron(0 2 * * ? *)"
            StartWindowMinutes: 60
            CompletionWindowMinutes: 120
            Lifecycle:
              DeleteAfterDays: 30
              MoveToColdStorageAfterDays: 7
            RecoveryPointTags:
              Environment: !Ref Environment
              BackupType: Daily
          - RuleName: WeeklyBackup
            TargetBackupVault: !Ref BackupVault
            ScheduleExpression: "cron(0 3 ? * SUN *)"
            StartWindowMinutes: 60
            CompletionWindowMinutes: 180
            Lifecycle:
              DeleteAfterDays: 90
              MoveToColdStorageAfterDays: 14
            CopyActions:
              - DestinationBackupVaultArn: !Sub "arn:aws:backup:${BackupRegion}:${AWS::AccountId}:backup-vault:${Environment}-backup-vault-${BackupRegion}"
                Lifecycle:
                  DeleteAfterDays: 365
                  MoveToColdStorageAfterDays: 30
            RecoveryPointTags:
              Environment: !Ref Environment
              BackupType: Weekly

  # Backup Role
  BackupRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: backup.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup
        - arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores

  # Backup Selection
  BackupSelection:
    Type: AWS::Backup::BackupSelection
    Properties:
      BackupPlanId: !Ref BackupPlan
      BackupSelection:
        SelectionName: !Sub "${Environment}-backup-selection"
        IamRoleArn: !GetAtt BackupRole.Arn
        Resources:
          - !Sub "arn:aws:rds:${AWS::Region}:${AWS::AccountId}:db:${Environment}-database"
          - !Sub "arn:aws:ec2:${AWS::Region}:${AWS::AccountId}:volume/*"
        Conditions:
          StringEquals:
            "aws:ResourceTag/Environment": !Ref Environment
```

## 💡 모범 사례 및 최적화

### 1. 스택 분할 전략
```yaml
Stack Architecture:
  Foundation Stack:
    - VPC, Subnets, Route Tables
    - Internet Gateway, NAT Gateway
    - Security Groups (기본)
    
  Security Stack:
    - IAM Roles and Policies
    - KMS Keys
    - Secrets Manager
    
  Database Stack:
    - RDS Instance
    - Database Subnet Groups
    - Database Security Groups
    
  Application Stack:
    - Auto Scaling Group
    - Application Load Balancer
    - Launch Templates
    
  Monitoring Stack:
    - CloudWatch Dashboards
    - CloudWatch Alarms
    - SNS Topics
```

### 2. 비용 최적화
```yaml
Cost Optimization Strategies:
  Tagging Strategy:
    - Environment: dev/staging/prod
    - Project: ProjectName
    - Owner: TeamName
    - CostCenter: DepartmentCode
    
  Resource Scheduling:
    - Dev environments: Stop after hours
    - Staging: Scale down during weekends
    - Prod: Reserved instances for predictable workloads
    
  Storage Optimization:
    - S3 Lifecycle policies
    - EBS volume optimization
    - RDS storage auto-scaling
```

### 3. 보안 모범 사례
```yaml
Security Best Practices:
  Least Privilege Access:
    - IAM roles with minimal permissions
    - Resource-specific policies
    - Cross-account access controls
    
  Network Security:
    - Private subnets for applications
    - Security groups with specific rules
    - NACLs for additional protection
    
  Data Protection:
    - Encryption at rest and in transit
    - KMS key rotation
    - Secrets Manager for credentials
    
  Monitoring:
    - CloudTrail for API logging
    - Config for compliance monitoring
    - GuardDuty for threat detection
```

## 📊 성능 및 비용 분석

### 1. 환경별 예상 비용
```yaml
월간 예상 비용:
  Development:
    - EC2 (t3.micro): $8
    - RDS (db.t3.micro): $12
    - ALB: $16
    - NAT Gateway: $32
    - 총 비용: ~$70/월
    
  Staging:
    - EC2 (t3.small): $16
    - RDS (db.t3.small): $24
    - ALB: $16
    - NAT Gateway: $32
    - 총 비용: ~$90/월
    
  Production:
    - EC2 (m5.large): $70
    - RDS (db.r5.large): $150
    - ALB: $16
    - NAT Gateway: $96 (3개)
    - 총 비용: ~$350/월
```

### 2. 리소스 사용량 최적화
```yaml
Resource Optimization:
  Auto Scaling:
    - CPU 기반 스케일링
    - 예측 스케일링 (프로덕션)
    - 스케줄 기반 스케일링
    
  Database:
    - Read Replica for read-heavy workloads
    - Connection pooling
    - Query optimization
    
  Storage:
    - GP3 volumes for better price/performance
    - EBS optimization
    - S3 Intelligent Tiering
```

## 🚀 실습 과제

### 1. 기본 구현 (1-2주)
1. **CloudFormation 템플릿 작성**
   - 네트워크 스택 구현
   - 보안 스택 구현
   - 애플리케이션 스택 구현

2. **CDK 애플리케이션 개발**
   - TypeScript CDK 앱 생성
   - 환경별 설정 구현
   - 단위 테스트 작성

### 2. CI/CD 파이프라인 구축 (2-3주)
1. **GitHub Actions 워크플로우 구현**
   - 브랜치별 배포 전략
   - 테스트 자동화
   - 보안 스캔 통합

2. **CodePipeline 구성**
   - 멀티 스테이지 파이프라인
   - 승인 프로세스
   - 롤백 전략

### 3. 모니터링 및 규정 준수 (1-2주)
1. **CloudWatch 모니터링**
   - 대시보드 구성
   - 알람 설정
   - 로그 집계

2. **AWS Config 규칙 구현**
   - 규정 준수 모니터링
   - 자동 교정
   - 보고서 생성

### 4. 재해 복구 구현 (2-3주)
1. **백업 전략 구현**
   - 크로스 리전 백업
   - 자동화된 복구
   - 테스트 절차

2. **멀티 리전 배포**
   - 액티브-패시브 구성
   - 데이터 복제
   - 장애 조치 테스트

이 포스트는 AWS SAA 시험에서 핵심적으로 다뤄지는 Infrastructure as Code 개념을 실제 금융 서비스 환경의 요구사항과 연결하여 제시했습니다. CloudFormation과 CDK를 모두 활용하여 실무에서 바로 적용할 수 있는 완전한 IaC 솔루션을 제공합니다.

---

**관련 포스트:**
- [AWS SAA 재해 복구 백업 전략](../29/aws-saa-disaster-recovery-backup-strategy)
- [AWS SAA Well-Architected 비용 최적화](../30/aws-saa-well-architected-cost-optimization)
