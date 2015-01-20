# -*- coding: utf-8 -*-

# import system
import os
import re
from fabric.api import env, task, roles, execute, run, put
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
    run('mkdir -p %s' % env.releases_dir)
    execute(cleanup)


@task
@roles('be')
def cleanup():
    """
    Remove releases antigos
    """
    remove = releases()[env.keep:]
    if remove:
        run('rm -rf %s/{%s}' % (env.releases_dir, ','.join(remove)))


@task
@roles('be')
def symlink(timestamp):
    """
        Cria link simbolico para o release current
    """
    run('rm -f %s' % env.current_dir)
    run('ln -s %s %s' % (os.path.join(env.releases_dir, timestamp), env.current_dir))


@task
@roles('be')
def releases():
    """
        Retorna todos os releases
    """
    result = run('ls %s' % env.releases_dir)
    releases_list = re.split('\s+', result)
    releases_list.sort(reverse=True)
    return releases_list


@task
@roles('be')
def current():
    """
        Retorna o release current
    """
    result = run("ls -ld %s | awk '{print $11}'" % env.current_dir)
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
        run('cd %s && git fetch --all' % env.source_dir)
    else:
        run('git clone %s %s' % (env.repository_url, env.source_dir))

    run('cd %s && git reset --hard && git pull origin master' % env.source_dir)
    run('cd %s && git archive --format=tar --prefix=%s/ HEAD | (cd %s && tar xf -)' % (env.source_dir, timestamp, env.releases_dir))


@task
@roles('be')
def pip_install():
    if not exists(env.virtualenv_dir):
        run('virtualenv %s' % env.virtualenv_dir)
    run('source %s/bin/activate; pip install -r %s/requirements.txt --no-deps' % (env.virtualenv_dir, env.current_dir))


@task
@roles('be')
def nginx():
    nginx_current_conf = "%s/conf/nginx/*" % env.current_dir
    sudo("cp %s %s" % (nginx_current_conf, env.nginx_dir))
    sudo("nginx -c %s/nginx.conf" % env.nginx_dir)


@task
@roles('be')
def supervisor(supervisor_conf_dir):
    # run('mkdir -p %s' % env.releases_dir, use_sudo=True)
    put('%s/*' % supervisor_conf_dir, '/etc/supervisor/conf.d', use_sudo=True)
    sudo('sudo supervisorctl reread')
    sudo('sudo supervisorctl update')
    sudo('sudo sysv-rc-conf supervisor on')
    sudo('supervisorctl reload admin')


@roles('be')
def create_directories(directories=None):
    if directories == None:
        directories = env.create_directories

    for folder in directories:
        if not exists(folder):
            run('mkdir -p %s' % folder)


@task
@roles('be')
def create_user():
    env.user = 'root'
    sudo('adduser dreasy')
    sudo('gpasswd -a dreasy sudo')
    sudo('mkdir /opt/dreasy')
    sudo('chown dreasy:dreasy /opt/dreasy')