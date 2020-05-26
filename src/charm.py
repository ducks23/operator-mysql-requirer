#!/usr/bin/env python3
import os
import socket
import sys
sys.path.append('lib')
sys.path.append('../lib')

import logging

from time import sleep

from pathlib import Path

from ops.charm import CharmBase

from ops.framework import (
    EventSource,
    EventBase,
    Object,
    ObjectEvents,
    StoredState,
)

from ops.main import main


logger = logging.getLogger()


class DBInfo:

    def __init__(
        self,
        user=None,
        password=None,
        host=None,
        port=None,
        database=None,
    ):
        self.set_address(user, password, host, port, database)

    def set_address(self, user, password, host, port, database):
        self._user = user
        self._password = password
        self._host = host
        self._port = port
        self._database = database

    @property
    def user(self):
        return self._user

    @property
    def password(self):
        return self._password

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def database(self):
        return self._database

    @classmethod
    def restore(cls, snapshot):
        return cls(
            user=snapshot['db_info.user'],
            password=snapshot['db_info.password'],
            host=snapshot['db_info.host'],
            port=snapshot['db_info.port'],
            database=snapshot['db_info.database'],
        )

    def snapshot(self):
        return {
            'db_info.user': self.user,
            'db_info.password': self.password,
            'db_info.host': self.host,
            'db_info.port': self.port,
            'db_info.database': self.database,
        }


class DBInfoAvailableEvent(EventBase):

    def __init__(self, handle, db_info):
        super().__init__(handle)
        self._db_info = db_info

    @property
    def db_info(self):
        return self._db_info

    def snapshot(self):
        return self.db_info.snapshot()

    def restore(self, snapshot):
        self._db_info = DBInfo.restore(snapshot)


class DBInfoEvents(ObjectEvents):
    db_info_available = EventSource(DBInfoAvailableEvent)


class MySQLClient(Object):
    """This class defines the functionality for the 'requires'
    side of the 'foo' relation.

    Hook events observed:
        - db-relation-created
        - db-relation-joined
        - db-relation-changed
    """
    on = DBInfoEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        # Observe the relation-changed hook event and bind
        # self.on_relation_changed() to handle the event.

        self.framework.observe(
            charm.on[relation_name].relation_created,
            self._on_relation_created
        )

        self.framework.observe(
            charm.on[relation_name].relation_joined,
            self._on_relation_joined
        )

        self.framework.observe(
            charm.on[relation_name].relation_changed,
            self._on_relation_changed
        )


    def _on_relation_created(self, event):
        logger.info(event.relation.__dict__)
        logger.info(event.relation.data.__dict__)


    def _on_relation_joined(self, event):
        logger.info(event.relation.__dict__)
        logger.info(event.relation.data.__dict__)


    def _on_relation_changed(self, event):
        """This method retrieves the value for 'foo'
        (set by the provides side of the relation) from the
        event.relation.data on the relation-changed hook event.
        """
        # Retrieve and log the value for 'foo' if it exists in
        # the relation data.

        while not event.relation.data.get(event.unit, None):
            sleep(1)
            logger.info("Waiting on mysql relation data")

        user = event.relation.data[event.unit].get('user', None)
        password = event.relation.data[event.unit].get('password', None)
        host = event.relation.data[event.unit].get('host', None)
        database = event.relation.data[event.unit].get('database', None)

        if (user and password and host and database):
            db_info = DBInfo(
                user=user,
                password=password,
                host=host,
                port="3306",
                database=database,
            )
            self.on.db_info_available.emit(db_info)
        else:
            logger.info("DB INFO NOT AVAILABLE")


class ConfigureSlurmEvent(EventBase):
    """Event used to signal that slurm config should be written to disk.
    """

class SlurmSnapInstalledEvent(EventBase):
    """Event used to signal that the slurm snap has been installed.
    """

class ConfigureSlurmEvents(ObjectEvents):
    configure_slurm = EventSource(ConfigureSlurmDBDEvent)
    slurm_snap_installed = EventSource(SlurmSnapInstalledEvent)


class SlurmSnapOps(Object):
    """Class containing events used to signal slurm snap configuration.

    Events emitted:
        - configure_slurm
    """
    on = ConfigureSlurmEvents()

    def install_slurm_snap(self):
        pass

    def render_slurm_config(self, source, target, context):
        """Render the context into the source template and write
        it to the target location.
        """

        source = Path(source)
        target = Path(target)

        if context and type(context) == dict:
            ctxt = context
        else:
            raise TypeError(
                f"Incorect type {type(context)} for context - Please debug."
            )

        if not source.exists():
            raise Exception(
                f"Source config {source} does not exist - Please debug."
            )

        if target.exists():
            target.unlink()

        with open(str(target), 'w') as f:
            f.write(open(str(source), 'r').read().format(**ctxt))


    def set_slurm_snap_mode(self, snap_mode):
        pass


class SlurmDBDCharm(CharmBase):
    """This charm demonstrates the 'requires' side of the relationship by
    extending CharmBase with an event object that observes
    the relation-changed hook event.
    """

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        self._stored.set_default(db_info=dict())

        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.install, self._on_install)

        self.db_info = MySQLClient(self, "db")
        self.framework.observe(
            self.db_info.on.db_info_available,
            self._on_db_info_available
        )

        self.slurm_ops = SlurmSnapOps(self, "slurm-config")
        self.framework.observe(
            self.slurm_ops.on.configure_slurm,
            self._on_configure_slurm
        )
        self.framework.observe(
            self.slurm_ops.on.slurm_snap_installed,
            self._on_slurm_snap_installed
        )

    def _on_install(self, event):
        pass

    def _on_start(self, event):
        pass

    def _on_slurm_snap_installed(self, event):
        pass

    def _on_db_info_available(self, event):
        """Store the db_info in the StoredState for later use.
        """
        db_info = {
            'user': event.db_info.user,
            'password': event.db_info.password,
            'host': event.db_info.host,
            'port': event.db_info.port,
            'database': event.db_info.database,
        }
        self._stored.db_info = db_info
        self.slurm_config.on.configure_slurm.emit()

    def _on_configure_slurm(self, event):
        """Render the slurmdbd.yaml and set the snap.mode.
        """
        hostname = socket.gethostname().split(".")[0]
        self.slurm_config.render_slurm_config(
            f"{os.getcwd()}/slurmdbd.yaml.tmpl",
            #"/var/snap/slurm/common/etc/slurm-configurator/slurmdbd.yaml",
            "/home/ubuntu/slurmdbd.yaml",
            context={**{"hostname": hostname}, **self._stored.db_info}
        )
        #self.slurm_config.set_slurm_snap_mode(
        #    "slurmdbd+manual"
        #)


if __name__ == "__main__":
    main(SlurmDBDCharm)
