# hscamera
high speed camera software

# Python environment guide
Requires the following libraries:
1. pyqt5
2. qtwidgets (https://github.com/MikeSmithLabTeam/qtwidgets)
3. labvision (https://github.com/MikeSmithLabTeam/labvision)
4. numpy

Add the following to the python content root
1. /opt/SiliconSoftware/Runtime5.7.0/SDKWrapper/PythonWrapper/python36/lib
2. /opt/ConfigFiles

# Linux Installation Guide

## Kernel must be 4.15
Install ubuntu mainline by 
``` 
sudo add-apt-repository ppa:cappelikan/ppa
sudo apt update
sudo apt install mainline
```
Run mainline and install 4.15

Change to kernel version by
```
sudo nano /etc/default/grub
```
change GRUB_TIMEOUT to -1 then run
```
sudo update-grub
sudo reboot
```
On reboot select advanced options then select 4.15 kernel


## Install drivers
1. download menable_linuxdrv_src_4.2.5.tar.bz2
2. Move to folder where you want the driver to be extracter
3. Extract with ```tar xjvf menable_linuxdrv_src_4.2.5.tar.bz2```
4. Enter the folder and run ```make && sudo make install```
5. Load the driver using ```sudo modprobe menable```
6. Check success with ```dmesg | grep menable```
7. Ensure the user is in the group video using ```sudo usermod -aG video <username>```

## Install runtime
1. download siso-rt5-5.6-linux-amd64.tar.bz2
2. download siso-rt5-5.6-linux-amd64-installer.sh
3. In the same folder run ```sudo ./siso-rt5-5.6.x-linux-amd64-installer.sh```. This will install into the default location /opt/SiliconSoftware

## Adapting the environment
1. Set SISODIR5 by ```export SISODIR5=/opt/SiliconSoftware/Runtime5.6.x```
2. Set the GeniCAm environment for runtime
```angular2html
export GENICAM_ROOT_V2_2=${SISODIR5}/genicam
export GENICAM_CACHE_V2_2=${SISODIR5}/genicam/cache
export
GENICAM_LOG_CONFIG_V2_2=${SISODIR5}/genicam/log/config/SisoLogging.prop
erties
``` 
3. To locate the corresponding modules PATH and LD_LIBRARY_PATH, use the following
commands
```angular2html
export PATH=${SISODIR5}/bin:${PATH}
export
LD_LIBRARY_PATH=${GENICAM_ROOT_V2_2}/bin/Linux64_x64:${SISODIR5}/lib
:${LD_LIBRARY_PATH}
```

## Adapting the environment automatically
1. To start the automatic setting of the necessary environment variables enter:
```source <INSTALLDIR>/setup-siso-env.sh ```

## Setting user access rights
```
sudo chown -R root:video <INSTALLDIR>/bin/log
sudo chmod -R g+w <INSTALLDIR>/bin/log
sudo chown -R root:video <INSTALLDIR>/genicam/cache
sudo chmod -R g+w <INSTALLDIR>/genicam/cache
```

## Start the generic service
```<INSTALLDIR>/bin/gs start```

