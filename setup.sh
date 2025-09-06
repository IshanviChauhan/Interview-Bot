#!/bin/bash

# Update package list
apt-get update

# Install system dependencies
apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    pkg-config \
    gcc \
    g++

# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel
pip install --upgrade build
