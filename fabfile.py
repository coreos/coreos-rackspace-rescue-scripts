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

def run_all(image_loc):
  setup_host()
  fetch_image(image_loc)
  burn_image()
  setup_grub()
