---
layout: "post"
title: "Installing Docker with Ansible"
date: 2019-07-12
---

Just putting that here as a reference ;) Remote servers are running Ubuntu 18.

```yaml
- name: Add an apt key for Docker
      apt_key:
        url: https://download.docker.com/linux/ubuntu/gpg
        state: present

- name: Add docker repository
  apt_repository:
    repo: deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable
    state: present

- name: Install Docker and docker-compose
  apt:
    name: "{{ packages }}"
    state: present
    update_cache: yes
  vars:
    packages:
      - docker-ce
      - docker-compose

- name: Add existing user to the docker group
  user:
    name: "{{ ansible_user }}"
    groups: docker
    append: yes

```
