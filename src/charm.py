#!/usr/bin/env python3
import sys
sys.path.append('lib')
sys.path.append('../lib')

import logging

from time import sleep

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


class MySQLRequires(Object):
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


class FooRequirerCharm(CharmBase):
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

        # Adds our requiring side of the relation, FooRequires to the charm.
        self.db_info = MySQLRequires(self, "db")
        self.framework.observe(
            self.db_info.on.db_info_available,
            self._on_db_info_available
        )

    def _on_start(self, event):
        pass

    def _on_install(self, event):
        pass

    def _on_db_info_available(self, event):
        db_info = {
            'user': event.db_info.user,
            'password': event.db_info.password,
            'host': event.db_info.host,
            'port': event.db_info.port,
            'database': event.db_info.database,
        }
        self._stored.db_info = db_info
        logging.info(db_info)


if __name__ == "__main__":
    main(FooRequirerCharm)
