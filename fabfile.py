from fabric.api import run, put

def setup_host():
  run('apt-get -y install parted')

def fetch_image(image_loc):
  run('curl %s | gunzip > /tmp/coreos.bin' % (image_loc))

def burn_image():
  run('dd if=/tmp/coreos.bin of=/dev/xvdb bs=128M')
  run('partprobe')

def setup_grub():
  run('mkdir -p /mnt/stateful')
  run('mount /dev/xvdb1 /mnt/stateful')
  run('mkdir -p /mnt/stateful/boot/grub')
  put('files/menu.lst', '/mnt/stateful/boot/grub/menu.lst')
  run('umount /mnt/stateful')
  run('rm -r /mnt/stateful')

def run_all(image_loc):
  setup_host()
  fetch_image(image_loc)
  burn_image()
  setup_grub()
