# User and Group Management Ansible Module

Overview

This Ansible module provides a flexible and secure way to manage users, groups, and their sudo privileges across systems. It supports both creation and cleanup of user groups with advanced configuration options.

Features:
 - Create and manage user groups
 - Define sudo privileges for groups
 - Add multiple users to groups
 - Cleanup mode to remove all configured groups and users
 - Supports flexible inventory configuration

Requirements
 - Ansible 2.9+
 - Linux-based target systems
 - Sudo access on target hosts

 HostOSconfiguration example:
```
 all:
  hosts:
    localhost:
      ansible_connection: local
  vars:
    values:
      cleanup_mode: false  # Set to true to remove all groups and users, no required 
      groups:
        - name: admins
          privileges: "ALL=(ALL) NOPASSWD: ALL"
          users:
            - user1
            - user2
```

Cleanup Mode (Remove All Configured Groups and Users)

cleanup_mode=Boolean - Remove all configured groups and users. Default="false".
