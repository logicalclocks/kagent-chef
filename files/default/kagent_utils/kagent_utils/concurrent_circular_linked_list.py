from threading import RLock

from circular_linked_list import CircularLinkedList

"""
Thread safe implementation of CircularLinkedList
"""
class ConcurrentCircularLinkedList(CircularLinkedList):
    def __init__(self):
        CircularLinkedList.__init__(self)
        self.lock = RLock()

    def add_first(self, data):
        try:
            self.lock.acquire()
            CircularLinkedList.add_first(self, data)
        finally:
            self.lock.release()

    def add(self, data):
        try:
            self.lock.acquire()
            CircularLinkedList.add(self, data)
        finally:
            self.lock.release()

    def poll(self):
        try:
            self.lock.acquire()
            return CircularLinkedList.poll(self)
        finally:
            self.lock.release()

    def peek(self):
        try:
            self.lock.acquire()
            return CircularLinkedList.peek(self)
        finally:
            self.lock.release()

    def get(self, index):
        try:
            self.lock.acquire()
            return CircularLinkedList.get(self, index)
        finally:
            self.lock.release()

    def index_of(self, data):
        try:
            self.lock.acquire()
            return CircularLinkedList.index_of(self, data)
        finally:
            self.lock.release()

    def remove_index(self, index):
        try:
            self.lock.acquire()
            return CircularLinkedList.remove_index(self, index)
        finally:
            self.lock.release()

    def remove(self, data):
        try:
            self.lock.acquire()
            return CircularLinkedList.remove(self, data)
        finally:
            self.lock.release()

    def clear(self):
        try:
            self.lock.acquire()
            CircularLinkedList.clear(self)
        finally:
            self.lock.release()

    def slice(self, size):
        try:
            self.lock.acquire()
            return CircularLinkedList.slice(self, size)
        finally:
            self.lock.release()

    def contains(self, data):
        try:
            self.lock.acquire()
            return CircularLinkedList.contains(self, data)
        finally:
            self.lock.release()
            
    def list_size(self):
        try:
            self.lock.acquire()
            return CircularLinkedList.list_size(self)
        finally:
            self.lock.release()

    def print_list(self):
        try:
            self.lock.acquire()
            CircularLinkedList.print_list(self)
        finally:
            self.lock.release()

    def __iter__(self):
        try:
            self.lock.acquire()
            CircularLinkedList.__iter__(self)
        finally:
            self.lock.release()
