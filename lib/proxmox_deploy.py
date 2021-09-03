from script_iso import ScriptIsoBuilder
import os
from cancamusa_host import HostInfo
import bios_cloner
from configuration import CancamusaConfiguration
import subprocess
from proxmox_utils import get_host_processor
from processors import list_processors
from PyInquirer import prompt


class ProxmoxDeployer:
    def __init__(self, project):
        project_path = project.config_path
        self.project = project
        self.project_path = os.path.join(project_path,"build")
        if not os.path.exists(self.project_path):
            os.mkdir(self.project_path)
        self.configuration = CancamusaConfiguration.load_or_create(None)

    def deploy_host(self, host):
        host_path = os.path.join(self.project_path,host.computer_name)
        if not os.path.exists(host_path):
            return
        qemu_template_file = os.path.join(host_path, str(host.host_id) + ".conf")
        if not os.path.exists(qemu_template_file):
            return
        # Copy QEMU template
        with open(qemu_template_file, 'r') as file_r:
            with open(os.path.join(self.configuration.proxmox_templates, os.path.basename(qemu_template_file)), 'w') as file_w:
                file_w.write(file_r.read())
        
        dcisc_i = 0 
        img_storage = [x for x in  self.configuration.proxmox_storages if x['name'] == self.configuration.proxmox_image_storage][0]['path']
        # Create qcow2 images
        for hdisk in host.disks:
            qemu_disk_qcow2("{}/images/{}/vm-{}-disk-{}.qcow2".format(img_storage,host.host_id,host.host_id,dcisc_i), hdisk.size)
            dcisc_i = dcisc_i + 1
        
    def create_pool(self):
        usr_cfg = "/etc/pve/user.cfg"
        name = safe_pool_name(self.project.project_name)
        mv_list = list(map(lambda x: str(x.host_id), self.project.hosts))
        usr_cfg_edit = ""
        with open(usr_cfg, 'r') as file_r:
            usr_cfg_edit = file_r.read()
        pool_pos = usr_cfg_edit.find("pool:{}::".format(name))
        if pool_pos < 0:
            usr_cfg_edit += "\npool:{}::{}::\n".format(name,",".join(mv_list))
        else:
            new_line_pos = usr_cfg_edit[pool_pos:].find("\n")
            if new_line_pos >= 0:
                usr_cfg_edit = usr_cfg_edit[:pool_pos] + "\npool:{}::{}::\n".format(name,",".join(mv_list)) + usr_cfg_edit[pool_pos + new_line_pos:]
            else:
                usr_cfg_edit = usr_cfg_edit[:pool_pos] + "\npool:{}::{}::\n".format(name,",".join(mv_list))
        with open(usr_cfg, 'w') as file_w:
                file_w.write(usr_cfg_edit)
    
    def create_cpu_if_not_exists(self):
        # Creates a new Proxmox CPU in /etc/pve/virtual-guest/cpu-models.conf called Cancamusa
        if 'CANCAMUSA_DEBUG' in os.environ:
            return
            
        cpu_edit = ""
        try:
            with open("/etc/pve/virtual-guest/cpu-models.conf", 'r') as file_r:
                cpu_edit = file_r.read()
        except:
            pass
        cpu_pos = cpu_edit.find("cpu-model: Cancamusa")
        if cpu_pos < 0:
            try:
                processor = get_host_processor()
            except:
                answer = prompt([{'type': 'list', 'name': 'option',
                          'message': 'Creating the "Cancamusa" processor. Select a QEMU cpu type:', 'choices': list_processors()}])
                processor = answer['option']
            cpu_edit += """
cpu-model: Cancamusa
    flags +sse;+sse2;-hypervisor
    phys-bits host
    hidden 1
    hv-vendor-id GenuineIntel
    reported-model {}

""".format(processor)
        with open("/etc/pve/virtual-guest/cpu-models.conf", 'w+') as file_w:
            file_w.write(cpu_edit)

def safe_pool_name(name):
    # TODO: improve safeguard
    return name.replace(" ","").replace("-","_")

def qemu_disk_qcow2(pth,size):
    if 'CANCAMUSA_DEBUG' in os.environ:
        return
    parent = os.path.dirname(pth)
    if not os.path.exists(parent):
        os.mkdir(parent)
    process = subprocess.Popen(["qemu-img","create","-f","qcow2",pth,str(size)], stdout=subprocess.PIPE)
    output, error = process.communicate()
    p_status = process.wait()
    process.terminate()
    
