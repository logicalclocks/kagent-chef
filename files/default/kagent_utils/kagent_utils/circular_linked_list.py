"""
Module implementing a circular linked list
"""
class Node:
    """
    A node of the CircularLinkedList that contains some data
    """
    def __init__(self, data=None):
        self.data = data
        self.next = None

class CircularLinkedList:
    def __init__(self):
        self.length = 0
        self.head = None
        self.tail = None
        self.current = None
        self.indexes = set()

    def add_first(self, data):
        """
        Add an item at the beginning of the list

        Parameters
        ----------
        data: Data to be inserted
        """
        
        if data in self.indexes:
            return
        new_node = Node(data)
        if self.head is None:
            # List is empty, point to itself
            self.head = new_node
            self.tail = new_node
            new_node.next = self.head
        else:
            new_node.next = self.head
            self.tail.next = new_node
            self.head = new_node
        self.length += 1
        self.indexes.add(data)

    def add(self, data):
        """
        Add an item at the end of the list

        Parameters
        ----------
        data: Data to be inserted
        """

        if data in self.indexes:
            return
        new_node = Node(data)
        if self.head is None:
            # list is empty, point to itself
            self.head = new_node
            self.tail = new_node
            new_node.next = self.head
        else:
            self.tail.next = new_node
            self.tail = new_node
            new_node.next = self.head
        self.indexes.add(data)
        self.length += 1

    def poll(self):
        """
        Get and remove the head of the list

        Returns
        -------
        The first item in the list or None if the list is empty
        """

        if self.head is None:
            return None
        tmp_node = self.head
        if self.current == tmp_node:
            self.current = tmp_node.next
        self.head = self.head.next
        self.tail.next = self.head
        self.indexes.remove(tmp_node.data)
        self.length -=1
        
        self._readjust_head_and_tail(tmp_node)
        
        return tmp_node.data

    def peek(self):
        """
        Get but not remove the head of the list

        Returns
        -------
        The first item in the list or None if the list is empty
        """

        if self.head is not None:
            return self.head.data
        return None

    def get(self, index):
        """
        Get item in the specified index. Item is not removed from the list

        Parameters
        ----------
        index: Zero based index of the item

        Returns
        -------
        Item at the specified index or None

        Raises
        ------
        Exception: When index is a negative number or greater than the length of the list
        """

        return self._get_node(index).data
    
    def _get_node(self, index):
        if index >= self.length or index < 0:
            raise Exception("Index out of bounds")
        tmp_node = self.head
        while tmp_node is not None:
            if index == 0:
                self._readjust_head_and_tail(tmp_node)
                return tmp_node
            tmp_node = tmp_node.next
            index -= 1

    def index_of(self, data):
        """
        Get the index of an item

        Parameters
        ----------
        data: Data to get the index in the list

        Returns
        -------
        Index of item or -1 if not found
        """

        search_node = Node(data)
        tmp_node = self.head
        counter = 0
        while tmp_node is not None and counter < self.length:
            if tmp_node.data == search_node.data:
                return counter
            tmp_node = tmp_node.next
            counter += 1
        return -1

    def remove_index(self, index):
        """
        Remove an item at the specified index from the list

        Parameters
        ----------
        index: Index of the item to be removed

        Returns
        -------
        Item at the specified index

        Raises
        ------
        Exception: When index is a negative number or greater than the length of the list
        """

        if index >= self.length or index < 0:
            raise Exception("Index out of bounds")
        tmp_node = self.head
        counter = index
        while tmp_node is not None:
            if counter == 0:
                if index == 0:
                    previous_node = self.head
                else:
                    previous_node = self._get_node(index - 1)
                previous_node.next = tmp_node.next
                if tmp_node == self.head:
                    self.head = tmp_node.next
                    self.tail.next = tmp_node.next
                if tmp_node == self.tail:
                    self.tail = previous_node
                if self.current == tmp_node:
                    self.current = tmp_node.next
                self._readjust_head_and_tail(tmp_node)
                self.length -= 1
                self.indexes.remove(tmp_node.data)
                return tmp_node.data
            tmp_node = tmp_node.next
            counter -= 1

    def remove(self, data):
        """
        Remove an item from the list

        Parameters
        ----------
        data: Item to be removed

        Returns
        -------
        Removed item or None if item was not found in the list
        """

        idx = self.index_of(data)
        if idx == -1:
            return None
        return self.remove_index(idx)

    def clear(self):
        """
        Clear the list
        """

        if self.head is None:
            return
        tmp_node = self.head
        while self.length > 0:
            next_node = tmp_node.next
            tmp_node.next = None
            self.length -= 1
        self.head = None
        self.tail = None
        self.current = None
        self.indexes.clear()

    def slice(self, size):
        """
        Get a slice of the list. Next time you call slice on the same list, it will
        return a slice beginning from the last item (excluded) of the previous slice.
        If the slice reaches the end of the list, it will circle from the beginning.

        Parameters
        ----------
        size: Size of the slice if length of the list is greater or equal to size

        Returns
        -------
        A set with a slice of the list
        """

        if self.length == 0:
            return None
        if size > self.length:
            size = self.length
        if self.current is None:
            self.current = self.head

        slice = set()
        for i in range(0, size):
            slice.add(self.current.data)
            self.current = self.current.next
        return slice


    def contains(self, data):
        """
        Check whether the list contains the item

        Parameters
        ----------
        data: Item to look for

        Returns
        -------
        True if list contains item, otherwise False
        """

        return data in self.indexes
    

    def list_size(self):
        """
        Get the length of the list

        Returns
        -------
        List length
        """

        return self.length

    def print_list(self):
        """
        Print all the items in the list. Primarily for debugging
        """

        tmp_node = self.head
        counter = self.length
        while tmp_node is not None and counter > 0:
            print("Node data: {0}".format(tmp_node.data))
            tmp_node = tmp_node.next
            counter -= 1
            
    # When a node is removed and the next of the current is itself
    # the list will be empty and we need to re-adjust head and tail
    def _readjust_head_and_tail(self, node):
        if node.next == node:
            self.head = None
            self.tail = None
            self.current = None

    def __iter__(self):
        tmp_node = self.head
        while tmp_node is not None:
            yield tmp_node.data
            tmp_node = tmp_node.next
