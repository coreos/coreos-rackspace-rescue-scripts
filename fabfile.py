from fabric.api import run, put, env, execute

from config import config
env.password = config['host_pass']
env.user = 'root'

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

def run_all(name, image_loc):
  node = create_node(name)
  #rescue_node(name)

  # fabric stuff
  _set_hosts_by_node(node)
  execute(setup_host)
  execute(fetch_image, image_loc)
  execute(burn_image)
  execute(setup_grub)

  unrescue_node(name)

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
  image = [i for i in images if i.name == 'Debian 6 (Squeeze)'][0]
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
