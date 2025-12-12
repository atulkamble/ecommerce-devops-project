# EKS Module
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${var.project_name}-cluster"
  cluster_version = var.eks_cluster_version

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true
  
  # Enable IRSA
  enable_irsa = true

  # Cluster access entry
  # To add the current caller identity as an administrator
  enable_cluster_creator_admin_permissions = true

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # EKS Managed Node Group(s)
  eks_managed_node_group_defaults = {
    instance_types = [var.node_instance_type]
    
    # We are using the IRSA created below for permissions
    # However, we have to deploy with the policy attached FIRST (when creating a fresh cluster)
    # and then turn this off after the cluster/node group is created. Without this initial policy,
    # the VPC CNI fails to assign IPs and nodes cannot join the cluster
    # See https://github.com/aws/containers-roadmap/issues/1666 for more context
    iam_role_attach_cni_policy = true
  }

  eks_managed_node_groups = {
    main = {
      name = "main-node-group"
      
      min_size     = var.node_group_min_capacity
      max_size     = var.node_group_max_capacity
      desired_size = var.node_group_desired_capacity

      instance_types = [var.node_instance_type]
      capacity_type  = "ON_DEMAND"

      # Launch template configuration
      create_launch_template = false
      launch_template_name   = ""

      disk_size = 50
      
      # Remote access cannot be specified with a launch template
      remote_access = {
        ec2_ssh_key               = aws_key_pair.eks_nodes.key_name
        source_security_group_ids = [aws_security_group.remote_access.id]
      }

      labels = {
        Environment = var.environment
        NodeGroup   = "main"
      }

      taints = {}

      tags = {
        ExtraTag = "EKS managed node group"
      }
    }
  }

  # aws-auth configmap
  manage_aws_auth_configmap = true

  aws_auth_roles = [
    {
      rolearn  = module.eks.eks_managed_node_groups.main.iam_role_arn
      username = "system:node:{{EC2PrivateDNSName}}"
      groups   = ["system:bootstrappers", "system:nodes"]
    },
  ]

  tags = var.tags
}

# Security group for remote access
resource "aws_security_group" "remote_access" {
  name_prefix = "${var.project_name}-remote-access-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"
    cidr_blocks = [
      "10.0.0.0/8",
      "172.16.0.0/12",
      "192.168.0.0/16",
    ]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-remote-access"
  })
}

# Create a key pair for EC2 instances
resource "tls_private_key" "eks_nodes" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "eks_nodes" {
  key_name   = "${var.project_name}-eks-nodes"
  public_key = tls_private_key.eks_nodes.public_key_openssh

  tags = var.tags
}

# Store private key in AWS Systems Manager Parameter Store
resource "aws_ssm_parameter" "eks_nodes_private_key" {
  name  = "/${var.project_name}/eks/nodes/private-key"
  type  = "SecureString"
  value = tls_private_key.eks_nodes.private_key_pem

  tags = var.tags
}