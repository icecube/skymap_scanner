#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

resource "aws_vpc" "pulsar_vpc" {
  cidr_block           = var.base_cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "Pulsar-VPC"
  }
}

resource "aws_default_network_acl" "default" {
  default_network_acl_id = aws_vpc.pulsar_vpc.default_network_acl_id

  egress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  egress {
    protocol   = -1
    rule_no    = 101
    action     = "allow"
    ipv6_cidr_block = "::/0"
    from_port  = 0
    to_port    = 0
  }

  ingress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  ingress {
    protocol   = -1
    rule_no    = 101
    action     = "allow"
    ipv6_cidr_block = "::/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name = "main"
  }
}

resource "aws_subnet" "default" {
  vpc_id                  = aws_vpc.pulsar_vpc.id
  cidr_block              = cidrsubnet(var.base_cidr_block, 8, 2)
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "Pulsar-Subnet"
  }
}

resource "aws_route_table" "default" {
  vpc_id = aws_vpc.pulsar_vpc.id

  tags = {
    Name = "Pulsar-Route-Table"
  }
}

resource "aws_route" "default" {
  route_table_id         = aws_route_table.default.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.default.id
}

resource "aws_route_table_association" "default" {
  subnet_id      = aws_subnet.default.id
  route_table_id = aws_vpc.pulsar_vpc.main_route_table_id
}

/* Misc */
resource "aws_eip" "default" {
  vpc        = true
  depends_on = [aws_internet_gateway.default]
}

resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.pulsar_vpc.id

  tags = {
    Name = "Pulsar-Internet-Gateway"
  }
}

resource "aws_nat_gateway" "default" {
  allocation_id = aws_eip.default.id
  subnet_id     = aws_subnet.default.id
  depends_on    = [aws_internet_gateway.default]

  tags = {
    Name = "Pulsar-NAT-Gateway"
  }
}

/* Public internet route */
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.pulsar_vpc.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.default.id
}


/* External network (public) load balancer */
resource "aws_elb" "default" {
  name            = "pulsar-elb"
  instances       = aws_instance.proxy.*.id
  security_groups = [aws_security_group.elb.id]
  subnets         = [aws_subnet.default.id]

  listener {
    instance_port     = 6650
    instance_protocol = "tcp"
    lb_port           = 6651
    lb_protocol       = "ssl"
    ssl_certificate_id = var.external_ssl_cert_arn
  }

  listener {
      instance_port      = 8080
      instance_protocol  = "http"
      lb_port            = 8443
      lb_protocol        = "https"
      ssl_certificate_id = var.external_ssl_cert_arn
    }
    
  cross_zone_load_balancing = false

  tags = {
    Name = "Pulsar-Load-Balancer"
  }
}

/*
resource "aws_lb" "pulsar_lb" {
  internal                          = false
  load_balancer_type                = "network"
  subnets                           = [aws_subnet.default.id]
  #ip_address_type                   = "dualstack"
  enable_cross_zone_load_balancing  = false
  
  tags = {
    Name = "Pulsar-Load-Balancer"
  }
}

resource "aws_lb_listener" "pulsar_lb_listener_QUEUE" {
  load_balancer_arn   = aws_lb.pulsar_lb.arn
  
  port                = 6651
  protocol            = "TLS"
  certificate_arn     = var.external_ssl_cert_arn
  ssl_policy          = "ELBSecurityPolicy-2016-08"
  
  default_action {
    target_group_arn = aws_lb_target_group.pulsar_lb_tg_QUEUE.arn
    type             = "forward"
  }
}

resource "aws_lb_target_group" "pulsar_lb_tg_QUEUE" {
  port         = 6650
  protocol     = "TCP"
  vpc_id       = aws_vpc.pulsar_vpc.id
  target_type  = "instance"
  deregistration_delay = 90
  
}

resource "aws_lb_target_group_attachment" "pulsar_lb_tga_QUEUE" {
  count = length(aws_instance.proxy)
  target_group_arn  = aws_lb_target_group.pulsar_lb_tg_QUEUE.arn
  target_id = aws_instance.proxy[count.index].id
}

resource "aws_lb_listener" "pulsar_lb_listener_ADMIN" {
  load_balancer_arn   = aws_lb.pulsar_lb.arn
  
  port                = 8443
  protocol            = "HTTPS"
  certificate_arn     = var.external_ssl_cert_arn
  ssl_policy          = "ELBSecurityPolicy-2016-08"
  
  default_action {
    target_group_arn = aws_lb_target_group.pulsar_lb_tg_ADMIN.arn
    type             = "forward"
  }
}

resource "aws_lb_target_group" "pulsar_lb_tg_ADMIN" {
  port         = 8080
  protocol     = "HTTP"
  vpc_id       = aws_vpc.pulsar_vpc.id
  target_type  = "instance"
  deregistration_delay = 90
  
}

resource "aws_lb_target_group_attachment" "pulsar_lb_tga_ADMIN" {
  count = length(aws_instance.proxy)
  target_group_arn  = aws_lb_target_group.pulsar_lb_tg_ADMIN.arn
  target_id = aws_instance.proxy[count.index].id
}
*/
