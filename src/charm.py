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


class FooAvailableEvent(EventBase):
    """Emitted when the value for 'foo' has been received."""


class FooEvents(ObjectEvents):
    foo_available = EventSource(FooAvailableEvent)



class MySQLRequires(Object):
    """This class defines the functionality for the 'requires'
    side of the 'foo' relation.

    Hook events observed:
        - db-relation-created
        - db-relation-joined
        - db-relation-changed
    """
    on = FooEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        # Observe the relation-changed hook event and bind
        # self.on_relation_changed() to handle the event.

        self.charm = charm

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
            db_info = {
                'user': user,
                'password': password,
                'host': host,
                'port': "3306",
                'database': database,
            }
            #self.charm._stored.db_info = db_info
            self.on.foo_available.emit(db_info)
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
        self.foo = MySQLRequires(self, "db")
        self.framework.observe(self.foo.on.foo_available, self.on_foo_available)

    def _on_start(self, event):
        pass

    def _on_install(self, event):
        pass

    def on_foo_available(self, event):
        logging.info(event.__dict__)


if __name__ == "__main__":
    main(FooRequirerCharm)
