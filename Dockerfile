FROM ubuntu:18.04
RUN apt-get -y update
RUN apt-get -y install python-pip
RUN apt-get -y install cython git
RUN apt-get -y install cython-dbg python-setuptools debhelper
RUN apt-get -y install python-all-dev python-all-dbg libasound2-dev libssl-dev
RUN apt-get -y install libv4l-dev libavcodec-dev libavformat-dev libavutil-dev
RUN apt-get -y install libswscale-dev libswresample-dev libx264-dev libvpx-dev libavcodec-extra
RUN apt-get -y install libgmp3-dev libmpfr-dev libmpc-dev pkg-config libsqlite3-dev python-pip darcs
RUN apt-get -y install libswresample-dev
RUN apt-get -y install libgmp3-dev
RUN apt-get -y install openssl 
RUN apt-get -y install libssl1.0-dev

RUN pip install -U pyopenssl
RUN pip install -U service_identity
RUN pip install -U python-gnutls python-otr dnspython twisted python-application cython python-dateutil greenlet

WORKDIR /usr/src
RUN darcs get http://devel.ag-projects.com/repositories/python-eventlib
WORKDIR /usr/src/python-eventlib
RUN python setup.py install

WORKDIR /usr/src
RUN darcs get http://devel.ag-projects.com/repositories/python-xcaplib
WORKDIR /usr/src/python-xcaplib
RUN python setup.py install

WORKDIR /usr/src
#RUN darcs get http://devel.ag-projects.com/repositories/python-msrplib
RUN apt -y install wget unzip
RUN wget https://github.com/AGProjects/python-msrplib/archive/release-0.19.2.zip
RUN unzip release-0.19.2.zip
WORKDIR /usr/src/python-msrplib-release-0.19.2
RUN python setup.py install

WORKDIR /usr/src
RUN git clone https://github.com/agumbe/python-sipsimple.git
WORKDIR /usr/src/python-sipsimple
RUN chmod +x deps/pjsip/configure
RUN chmod +x deps/pjsip/aconfigure
RUN python setup.py build_ext --pjsip-clean-compile
RUN python setup.py build
RUN python setup.py install

WORKDIR /usr/src/py-psap
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD python sylk-server






