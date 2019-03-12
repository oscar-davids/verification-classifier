This repo contains a Dockerfile to make easy the interaction with the experiments.

##Build the image
To build the image, we have to type the following in the same folder of the repo:
```
docker build -t epicjupiter:v1 .
```

This will create a image based on `jupyter/datascience-notebook` but adding the needed python dependencies.

## Run the image
To run the image, we have to type
```
docker run -p 8888:8888 --volume="$(pwd)":/home/jovyan/work/ epicjupiter:v1
```

This will run the image on the port 8888 and mounts a volume with the contents of this repo in the folder `/home/jovyan/work/` which is accesible by jupyter and all the notebooks here will be acesible.

## Note on notebooks

### Compare_videos notebook

This notebook expects the videos to be in the data folder with the following structure

```
data
├── 3
│   └── 01.mp4
├── 4
│   └── 01.mp4
├── 5
│   └── 01.mp4
├── 6
│   └── 01.mp4
└── 7
    └── 01.mp4
```

Where

7 is the folder for the 1080p rendition (the original to compare against)
6 is the folder for the 720p rendition
5 is the folder for the 480p rendition
4 is the folder for the 360p rendition
3 is the folder for the 240p rendition

The result will be in the output folder

### Metric analysis notebook

This notebook expects a file `metrics.csv` in the output folder

## Multi scale ssim

There is a script `evaluate-ms-ssim.sh` in order to calculate the multiscale ssim. This script receives one parameter
which is the path where the videos are with the same structure as mentioned in [Compare_videos notebook](#Compare_videos notebook).

```
bash evaluate-ms-ssim.sh /path/to/videos

```

The script will produce the following folder structure:

```
mssim
├── 240
│   ├── -8ygLPzgpsg
│   │   └── -8ygLPzgpsg_240.log
├── 360
│   ├── -8ygLPzgpsg
│   │   └── -8ygLPzgpsg_360.log
├── 480
│   ├── -8ygLPzgpsg
│   │   └── -8ygLPzgpsg_480.log
└── 720
    ├── -8ygLPzgpsg
        └── -8ygLPzgpsg_720.log 
```

Where the folder indicates the rendition we are using to compare against the original (1080). 
A subfolder of this folder contains the name of the asset and finally the file containing the log.

The log is a csv file, with the following structure:

```
ms-ssim, psnr-y, psnr-u, psnr-v
0.986889, 32.866684, 43.274622, 42.429359
0.985558, 32.394349, 43.344157, 42.658971
0.985460, 32.521368, 43.338460, 42.580399
0.985896, 32.670122, 43.325404, 42.529248
```

In order to work, this script needs a version of avconv that contains the ms-ssim which can be found 
[here](https://github.com/lu-zero/libav/tree/mea) and the livepeer 
[TranscodingVerification](https://github.com/livepeer/TranscodingVerification) 

Some basics steps to build it in mac osx

### TranscodingVerification

```
brew install meson
git clone https://github.com/livepeer/TranscodingVerification.git
cd TranscodingVerification
meson .build
ninja -C .build install
```

### libav

```
brew install pkgconfig
git clone https://github.com/lu-zero/libav.git
cd libav
git checkout mea
./configure --enable-libmea
make && make install
```


## Vmaf

There is a script `evaluate-vmaf.sh` in order to calculate the vmaf score. This script receives one parameter
which is the path where the videos are with the same structure as mentioned in [Compare_videos notebook](#Compare_videos notebook).

```
bash evaluate-vmaf.sh /path/to/videos

```

The script will produce the following folder structure:

```
output/vmaf
├── 240
│   ├── -8ygLPzgpsg
│   │   ├── -8ygLPzgpsg_240.log
│   │   └── -8ygLPzgpsg_240.log.out
├── 360
│   ├── -8ygLPzgpsg
│   │   ├── -8ygLPzgpsg_360.log
│   │   └── -8ygLPzgpsg_360.log.out
├── 480
│   ├── -8ygLPzgpsg
│   │   ├── -8ygLPzgpsg_480.log
│   │   └── -8ygLPzgpsg_480.log.out
└── 720
    ├── -8ygLPzgpsg
        ├── -8ygLPzgpsg_720.log
        └── -8ygLPzgpsg_720.log.out
```

Where the folder indicates the rendition we are using to compare against the original (1080). 
A subfolder of this folder contains the name of the asset and finally two files: One containing the result 
(videoname_rendition.log) and other containing the output from the ffmpeg (videoname_rendition.log.out).

The log file contains the following information:

```
Start calculating VMAF score...
Exec FPS: 158.922597
VMAF score = 90.566873
```

The interesting line is the third one, containing the vmaf score.

The .out file is not worth analyzing as it is the standard ffmpeg output

In order to function, this script needs [vmaf](https://github.com/Netflix/vmaf.git) and 
[ffmpeg](https://git.ffmpeg.org/ffmpeg.git) installed. 

Some basics steps to build it in mac osx

### vmaf
```
git clone https://github.com/Netflix/vmaf.git
cd vmaf
make && make install
```


### ffmpeg
```
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg
./configure --enable-libvmaf --enable-version3
make && make install
```