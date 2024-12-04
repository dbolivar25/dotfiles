function load_openstack
    functions -e openstack ansible ansible-playbook
    bass source ~/.config/openstack/openstackrc.sh
end
