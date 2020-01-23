resource "aws_route53_record" "pulsar" {
  zone_id = var.route53_zone_id
  name = var.external_dns_name
  type = "CNAME"
  ttl = "30"
  records = ["dualstack.${aws_elb.default.dns_name}"]
}
