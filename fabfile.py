from fabric.api import run, put, env, execute, cd

from fabric.operations import open_shell

from config import config
env.password = config['host_pass']
env.user = 'root'

def ssh(name):
  _set_hosts_by_name(name)
  execute(open_shell)

def setup_host():
  run('apt-get -y install parted')

def fetch_image(image_loc):
  run('curl %s | gunzip > /tmp/coreos.bin' % (image_loc))

def burn_image():
  run('dd if=/tmp/coreos.bin of=/dev/xvdb bs=128M')
  run('partprobe')

def setup_grub():
  run('mkdir -p /mnt/stateful')
  run('mkdir -p /mnt/root')
  run('mount /dev/xvdb1 /mnt/stateful')
  run('mount /dev/xvdb3 /mnt/root')
  run('mkdir -p /mnt/stateful/boot/grub')
  put('files/menu.lst', '/mnt/stateful/boot/grub/menu.lst')
  run('cp /mnt/root/boot/vmlinuz /mnt/stateful/boot/vmlinuz')
  run('umount /mnt/stateful')
  run('umount /mnt/root')
  run('rm -r /mnt/stateful')
  run('rm -r /mnt/root')

def setup_networking():
  run('mkdir -p /mnt/root')
  run('mount /dev/xvdb3 /mnt/root')

  ip = run('ifconfig eth0 |grep "inet "|awk \'{print $2}\'|awk -F":" \'{print $2}\'')
  netmask = run('ifconfig eth0 |grep "inet "|awk \'{print $4}\'|awk -F":" \'{print $2}\'')
  gw = run('route -n | grep eth0 | grep "^0.0" | awk \'{ print $2 }\'')
  print ip, netmask, gw
  hack_network_script = """#!/bin/bash
ifconfig eth0 %s netmask %s
route add default gw %s """ % (ip, netmask, gw)


  run('echo \'%s\' > /mnt/root/sbin/coreos_rackspace_networking_hack.sh' % hack_network_script)
  run('chmod +x /mnt/root/sbin/coreos_rackspace_networking_hack.sh')
 
  put('files/usr/lib/systemd/system/rackspace-networking-hack.service', 
      '/mnt/root/usr/lib/systemd/system/rackspace-networking-hack.service')

  with cd('/mnt/root/usr/lib/systemd/system/basic.target.wants/'):
    run('ln -s ../rackspace-networking-hack.service ./rackspace-networking-hack.service')

  run('rm -f /mnt/root/usr/lib/systemd/system/multi-user.target.wants/dhcpcd.service')
  run('cp /etc/resolv.conf /mnt/root/etc/resolv.conf')

  run('umount /mnt/root')
  run('rm -r /mnt/root')
  
def run_all(name, image_loc):
  node = create_node(name)
  rescue_node(name)

  # fabric stuff
  _set_hosts_by_node(node)
  execute(setup_host)
  execute(fetch_image, image_loc)
  execute(burn_image)
  execute(setup_grub)
  execute(setup_networking)

  #unrescue_node(name)

def run_from_ami(name):
  _set_hosts_by_name(name)

  # pull image from ami
  execute(fetch_from_ami)

  execute(burn_image)
  execute(setup_grub)
  execute(setup_networking)

def build_ami(name, image_loc):
  _set_hosts_by_name(name)
#  execute(fetch_image, image_loc)
  execute(burn_image)
  execute(setup_grub_ami)

  
def fetch_from_ami():
  execute(put, config['aws_pk'], '/tmp/aws-pk.pem')
  execute(run, 'mkdir -p /tmp/coreos-ami')
#  execute(run, 'ec2-download-bundle -b coreos-img -a %s -s %s -k /tmp/aws-pk.pem -m chromiumos_image.bin.manifest.xml -d /tmp/coreos-ami/' % (config['aws_access_key'], config['aws_secret_key']))
  execute(run, 'ec2-unbundle -k /tmp/aws-pk.pem -m /tmp/coreos-ami/chromiumos_image.bin.manifest.xml -s /tmp/coreos-ami/ -d /tmp/coreos-ami/')
  execute(run, 'mv /tmp/coreos-ami/chromiumos_image.bin /tmp/coreos.bin')

# libcloud helper to setup libcloud driver
def _get_rack_driver():
  import libcloud.compute.providers
  import libcloud.security
  libcloud.security.CA_CERTS_PATH.append('dist/cacert.pem')
  CompRackspace = libcloud.compute.providers.get_driver(libcloud.compute.types.Provider.RACKSPACE_NOVA_DFW)
  compdriver = CompRackspace(config['api_user'], config['api_key'],
    ex_force_auth_url='https://identity.api.rackspacecloud.com/v2.0/',
    ex_force_auth_version='2.0')
  return compdriver

# fabric helper, will setup env.hosts using the given libcloud node
def _set_hosts_by_node(node):
  import socket
  for ip in node.public_ips:
    try:
      socket.inet_aton(ip)
      env.hosts = [str(ip)]
    except socket.error:
      pass

def _set_hosts_by_name(name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  _set_hosts_by_node(nodes[0])

# test libcloud/fabric integration
def test_node(name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  set_hosts_by_node(nodes[0])
  execute(uname)

def uname():
  run('uname -a')

# libcloud specific functions
def create_node(name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  if len(nodes) > 0 and nodes[0].name == name:
    return nodes[0]

  images = driver.list_images() 
  sizes = driver.list_sizes()
  image = [i for i in images if i.name == 'Debian 6.06 (Squeeze)'][0]
  size = [s for s in sizes if s.ram == 512][0]
  node = driver.create_node(name=name, size=size, image=image)
  nodes = driver.wait_until_running(nodes=[node])
  return nodes[0][0]

def show_node(name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  if len(nodes) != 1:
    raise 'Node %s not found' % (name)
  print nodes[0]

def rescue_node(name):
  import time
  from libcloud.compute.types import NodeState
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  if len(nodes) != 1:
    raise 'Node %s not found' % (name)
  node = nodes[0]
  driver.ex_rescue(node, password=config['host_pass'])
  # wait until it is in rescue mode
  while node.state != NodeState.PENDING:
    node = [x for x in driver.list_nodes() if x.name == name][0]
    time.sleep(3)

def unrescue_node(name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  if len(nodes) != 1:
    raise 'Node %s not found' % (name)
  node = nodes[0]
  driver.ex_unrescue(node)

def destroy_node(name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  if len(nodes) != 1:
    raise 'Node %s not found' % (name)
  node = nodes[0]
  driver.destroy_node(node)
