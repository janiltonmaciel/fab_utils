# -*- coding: utf-8 -*-

# import system
import os
import re
from fabric.api import env, task, roles, execute, run, put, cd
from fabric.contrib.files import exists
from fabric.operations import sudo



# __all__ = ['setup', 'cleanup', 'symlink', 'releases', 'current', 'previous',
            # 'rollback', 'clone_project', 'pip_install']


@task
@roles('be')
def init():
    """
        Setup inicial de deploy
    """
    run('mkdir -p %(releases_dir)s' % env)
    execute(cleanup)
    execute(create_directories)

@task
@roles('be')
def cleanup():
    """
    Remove releases antigos
    """
    remove = releases()[env.keep:]
    if remove:
        with cd(env.releases_dir):
            for release in remove:
                run('rm -rf %s' % release)


@task
@roles('be')
def symlink(timestamp):
    """
        Cria link simbolico para o release current
    """
    if exists(env.current_dir):
        run('rm -r %(current_dir)s' % env)
    run('ln -s %s %s' % (os.path.join(env.releases_dir, timestamp), env.current_dir))


@task
@roles('be')
def releases():
    """
        Retorna todos os releases
    """
    result = run('ls %(releases_dir)s' % env)
    releases_list = re.split('\s+', result)
    releases_list.sort(reverse=True)
    return releases_list


@task
@roles('be')
def current():
    """
        Retorna o release current
    """
    result = run("ls -ld %(current_dir)s | awk '{print $11}'" % env)
    return result.split('/')[-1]


@task
@roles('be')
def previous():
    """
        Retorna o release anterior ao current
    """
    releases_list = releases()
    try:
        return releases_list[-2]
    except IndexError:
        return None


@task
@roles('be')
def rollback():
    """
        Troca o release current pelo previous
    """
    current_timestamp = current()
    previous_timestamp = previous()

    if previous_timestamp:
        execute(symlink, *(previous_timestamp, ))
        run('rm -rf %s' % os.path.join(env.releases_dir, current_timestamp))


@task
@roles('be')
def clone_project(timestamp):
    if exists(env.source_dir + '/.git'):
        run('cd %(source_dir)s && git fetch --all' % env)
    else:
        run('git clone %(repository_url)s %(source_dir)s' % env)

    with cd(env.source_dir):
        run('git reset --hard && git pull origin master')
        run('git archive --format=tar --prefix=%s/ HEAD | (cd %s && tar xf -)' % (timestamp, env.releases_dir))


@task
@roles('be')
def pip_install(no_deps=True):
    if not exists(env.virtualenv_dir):
        run('virtualenv %(virtualenv_dir)s' % env)
        if no_deps:
            run('source %(virtualenv_dir)s/bin/activate; pip install -r %(current_dir)s/requirements.txt --no-deps' % env)
        else:
            run('source %(virtualenv_dir)s/bin/activate; pip install -r %(current_dir)s/requirements.txt' % env)


@task
@roles('be')
def nginx():
    nginx_conf = "%(current_dir)s/conf/nginx/nginx.conf" % env
    sudo("cp %s /etc/nginx/" % nginx_conf)
    sudo("service nginx restart")


@task
@roles('be')
def supervisor():
    supervisor_conf = "%s/conf/supervisor/supervisord.conf" % env.current_dir
    sudo("cp %s /etc/supervisor/" % supervisor_conf)

    supervisor_inc_dir = "%s/conf/supervisor/*.ini" % env.current_dir
    sudo("cp %s /etc/supervisor/conf.d/" % supervisor_inc_dir)
    sudo("service supervisor restart")


@roles('be')
def create_directories(directories=None):
    if directories == None:
        directories = env.create_directories

    for folder in directories:
        if not exists(folder):
            run('mkdir -p %s' % folder)


@task
@roles('be')
def create_user(user, isSudo=True):
    env.user = 'root'
    sudo('adduser %s' % user)
    sudo('mkdir /opt/%s' % user)
    sudo('chown %s:%s /opt/%s' % (user, user, user))
    if isSudo:
        sudo('gpasswd -a %s sudo' % user)


@task
@roles('be')
def provision():
    temp_dir = "/tmp/"
    provision_name = "provision.sh"
    put("%s/%s" % (env.provision_dir, provision_name), temp_dir)

    with cd(temp_dir):
        sudo("chmod +x %s && ./%s" % (provision_name, provision_name))
