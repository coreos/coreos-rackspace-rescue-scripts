from fabric.api import run, put, env, execute, cd, sudo

from fabric.operations import open_shell

from config import config
import time
env.password = config['host_pass']
env.user = 'root'

def ssh(name):
  _set_hosts_by_name(name)
  execute(open_shell)

def setup_host():
  run('apt-get update')
  run('apt-get -y install curl bzip2')

def fetch_image_dd(image_loc):
  run('curl %s | bunzip2 | dd of=/dev/xvdb bs=128M' % (image_loc))

def run_all(image_name, image_loc):
  name = 'auto'
  node = create_node(name)
  rescue_node(name)

#  ssh(name)
  # fabric stuff
  _set_hosts_by_node(node)
  execute(setup_host)
  execute(fetch_image_dd, image_loc)

  unrescue_node(name)
  new_node = save_and_create(name, image_name)

  # will try to ssh to the machine and run uname
  # will only work if the default password is falkor
  _set_hosts_by_node(new_node)
  env.user = 'core'
  execute(uname)


def save_and_create(base_name, image_name):
  image = save_image(base_name, image_name)
  while True:
    try:
      new_node = create_node(image_name, image)
      print "created new node with image...", new_node
      return new_node
    except Exception:
      print "waiting on image to be ready..."
      time.sleep(10)

def save_image(name, image_name):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  nodes = driver.wait_until_running(nodes=nodes)
  node = nodes[0][0]
  return driver.ex_save_image(node, image_name)

# libcloud helper to setup libcloud driver
def _get_rack_driver():
  import libcloud.compute.providers
  import libcloud.security
  libcloud.security.CA_CERTS_PATH.append('dist/cacert.pem')
  CompRackspace = libcloud.compute.providers.get_driver(libcloud.compute.types.Provider.RACKSPACE_NOVA_ORD)
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
  run('grep VERSION /etc/lsb-release')

# libcloud specific functions
def create_node(name, image=None):
  driver = _get_rack_driver()
  nodes = [x for x in driver.list_nodes() if x.name == name]
  if len(nodes) > 0 and nodes[0].name == name:
    return nodes[0]

  sizes = driver.list_sizes()
  #size = [s for s in sizes if s.id == 'performance1-1'][0]
  size = [s for s in sizes if s.id == 'performance1-2'][0]
  if image is None:
    images = driver.list_images() 
    image = [i for i in images if i.name == 'Debian 7 (Wheezy) (PVHVM)'][0]
#    image = [i for i in images if i.name == 'Debian 6.06 (Squeeze)'][0]
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
  # wait for ssh to come up
  time.sleep(10)

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
