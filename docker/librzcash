FROM ubuntu:16.04

# Update default packages
RUN apt-get update

# Get Ubuntu packages
RUN apt-get install -y \
    build-essential \
    curl \
    git \
    nano

# Update new packages
RUN apt-get update

# Get Rust
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

RUN echo 'source $HOME/.cargo/env' >> $HOME/.bashrc

ENV PATH /root/.cargo/bin:$PATH

WORKDIR /home

RUN git clone https://github.com/zcash/librustzcash.git

WORKDIR /home/librustzcash/librustzcash

RUN cargo build --lib

