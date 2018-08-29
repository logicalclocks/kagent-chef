import unittest

from parameterized import parameterized

from kagent_utils import CircularLinkedList
from kagent_utils import ConcurrentCircularLinkedList

class TestCircularLinkedList(unittest.TestCase):

    def _test_params():
        return [("non-thread_safe", 0),
                ("thread_safe", 1)
        ]
    
    def _setUp(self, mode):
        if mode == 0:
            self.list = CircularLinkedList()
        elif mode == 1:
            self.list = ConcurrentCircularLinkedList()
        self._assert_empty()
    
    @parameterized.expand(_test_params)
    def test_add_first(self, name, mode):
        self._setUp(mode)
        self.list.add_first("Node1")
        self._assert_list_size(1)

        self.assertEquals("Node1", self.list.head.data)
        self.assertEquals("Node1", self.list.tail.data)
                
        # It's a circular list so it should point to itself
        self.assertEquals("Node1", self.list.head.next.data)
        self.assertEquals("Node1", self.list.tail.next.data)

        # Add a second node first
        self.list.add_first("Node0")
        self._assert_list_size(2)

        self.assertEquals("Node0", self.list.head.data)
        self.assertEquals("Node1", self.list.head.next.data)
        self.assertEquals("Node0", self.list.head.next.next.data)
        
        self.assertEquals("Node1", self.list.tail.data)
        self.assertEquals("Node0", self.list.tail.next.data)
        self.assertEquals("Node1", self.list.tail.next.next.data)

    @parameterized.expand(_test_params)
    def test_add(self, name, mode):
        self._setUp(mode)
        self.list.add("Node0")
        self._assert_list_size(1)

        self.assertEquals("Node0", self.list.head.data)
        self.assertEquals("Node0", self.list.tail.data)

        self.assertEquals("Node0", self.list.head.next.data)
        self.assertEquals("Node0", self.list.tail.next.data)

        # Add a second node
        self.list.add("Node1")
        self._assert_list_size(2)

        self.assertEquals("Node0", self.list.head.data)
        self.assertEquals("Node1", self.list.tail.data)

        self.assertEquals("Node1", self.list.head.next.data)
        self.assertEquals("Node0", self.list.tail.next.data)
        self.assertEquals("Node0", self.list.head.next.next.data)
        self.assertEquals("Node1", self.list.tail.next.next.data)

    @parameterized.expand(_test_params)
    def test_add_first_unique(self, name, mode):
        self._setUp(mode)
        self.list.add_first("Node1")
        self._assert_list_size(1)
        self.assertTrue("Node1" in self.list.indexes)
        self.list.add_first("Node1")
        self._assert_list_size(1)
        self.assertEquals(1, len(self.list.indexes))

        self.list.remove("Node1")
        self._assert_empty()
        self.assertFalse("Node1" in self.list.indexes)
        self.assertEquals(0, len(self.list.indexes))

        self.list.add_first("Node1")
        self._assert_list_size(1)
        self.assertTrue("Node1" in self.list.indexes)
        self.assertEquals(1, len(self.list.indexes))

    @parameterized.expand(_test_params)
    def test_add_unique(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self._assert_list_size(1)
        self.assertTrue("Node1" in self.list.indexes)
        self.list.add("Node1")
        self._assert_list_size(1)
        self.assertEquals(1, len(self.list.indexes))

        self.list.remove_index(0)
        self._assert_empty()
        self.assertFalse("Node1" in self.list.indexes)
        self.assertEquals(0, len(self.list.indexes))

        self.list.add("Node1")
        self._assert_list_size(1)
        self.assertTrue("Node1" in self.list.indexes)
        self.assertEquals(1, len(self.list.indexes))

    @parameterized.expand(_test_params)
    def test_peek_add(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self._assert_list_size(1)

        first = self.list.peek()
        self.assertEquals("Node1", first)
        self._assert_list_size(1)

        self.list.add("Node2")
        first = self.list.peek()
        self.assertEquals("Node1", first)
        self._assert_list_size(2)

    @parameterized.expand(_test_params)
    def test_peek_add_first(self, name, mode):
        self._setUp(mode)
        self.list.add_first("Node1")
        self._assert_list_size(1)

        first = self.list.peek()
        self.assertEquals("Node1", first)
        self._assert_list_size(1)

        self.list.add_first("Node0")
        first = self.list.peek()
        self.assertEquals("Node0", first)
        self._assert_list_size(2)

    @parameterized.expand(_test_params)
    def test_poll_add(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        first = self.list.poll()
        self.assertEquals("Node1", first)
        self._assert_empty()

        self.list.add("Node2")
        self.list.add("Node3")
        self._assert_list_size(2)
        first = self.list.poll()
        self.assertEquals("Node2", first)
        self._assert_list_size(1)

        first = self.list.poll()
        self.assertEquals("Node3", first)
        self._assert_empty()

    @parameterized.expand(_test_params)
    def test_poll_add_first(self, name, mode):
        self._setUp(mode)
        self.list.add_first("Node0")
        first = self.list.poll()
        self.assertEquals("Node0", first)
        self._assert_empty()

        self.list.add_first("Node1")
        self.list.add_first("Node2")
        self._assert_list_size(2)
        first = self.list.poll()
        self.assertEquals("Node2", first)
        self._assert_list_size(1)
        first = self.list.poll()
        self.assertEquals("Node1", first)
        self._assert_empty()

    @parameterized.expand(_test_params)
    def test_peek_add(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self._assert_list_size(2)

        first = self.list.peek()
        self.assertEquals("Node1", first)
        self._assert_list_size(2)
        first2 = self.list.peek()
        self.assertEquals(first, first2)
        self._assert_list_size(2)

    @parameterized.expand(_test_params)
    def test_peek_add_first(self, name, mode):
        self._setUp(mode)
        self.list.add_first("Node1")
        self.list.add_first("Node2")
        self._assert_list_size(2)

        first = self.list.peek()
        self.assertEquals("Node2", first)
        self._assert_list_size(2)
        first2 = self.list.peek()
        self.assertEquals(first, first2)
        self._assert_list_size(2)

    @parameterized.expand(_test_params)
    def test_poll_empty_list(self, name, mode):
        self._setUp(mode)
        first = self.list.poll()
        self.assertIsNone(first)

        self.list.add("Node1")
        self.list.poll()
        first = self.list.poll()
        self._assert_empty()
        self.assertIsNone(first)

        self.list.add("Node2")
        self.list.poll()
        first = self.list.poll()
        self._assert_empty()
        self.assertIsNone(first)

    @parameterized.expand(_test_params)
    def test_peek_empty_list(self, name, mode):
        self._setUp(mode)
        first = self.list.peek()
        self.assertIsNone(first)

    @parameterized.expand(_test_params)
    def test_get_empty(self, name, mode):
        self._setUp(mode)
        with self.assertRaises(Exception) as ex:
            node = self.list.get(0)

    @parameterized.expand(_test_params)
    def test_get_negative_number(self, name, mode):
        self._setUp(mode)
        with self.assertRaises(Exception) as ex:
            node = self.list.get(-1)

    @parameterized.expand(_test_params)
    def test_get_index_out_of_bounds(self, name, mode):
        self._setUp(mode)
        self.list.add_first("Node1")
        self.list.add("Node2")
        with self.assertRaises(Exception) as ex:
            self.list.get(2)

    @parameterized.expand(_test_params)
    def test_get(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        node = self.list.get(1)
        self.assertEquals("Node2", node)
        self._assert_list_size(2)

    @parameterized.expand(_test_params)
    def test_index_of_empty(self, name, mode):
        self._setUp(mode)
        idx = self.list.index_of("SomeNode")
        self.assertEquals(-1, idx)

    @parameterized.expand(_test_params)
    def test_index_not_found(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        idx = self.list.index_of("SomeNode")
        self.assertEquals(-1, idx)

    @parameterized.expand(_test_params)
    def test_index_found(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        idx = self.list.index_of("Node2")
        self.assertEquals(1, idx)

    @parameterized.expand(_test_params)
    def test_list_size(self, name, mode):
        self._setUp(mode)
        self.assertEquals(0, self.list.list_size())
        self.list.add("Node1")
        self.assertEquals(1, self.list.list_size())
        self.list.add_first("Node2")
        self.assertEquals(2, self.list.list_size())

        self.list.get(1)
        self.assertEquals(2, self.list.list_size())
        self.list.poll()
        self.assertEquals(1, self.list.list_size())

    @parameterized.expand(_test_params)
    def test_remove_index_empty_list(self, name, mode):
        self._setUp(mode)
        with self.assertRaises(Exception) as ex:
            self.list.remove_index(0)

    @parameterized.expand(_test_params)
    def test_remove_index_negative(self, name, mode):
        self._setUp(mode)
        with self.assertRaises(Exception) as ex:
            self.list.remove_index(-1)

    @parameterized.expand(_test_params)
    def test_remove_index_out_of_bounds(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        with self.assertRaises(Exception) as ex:
            self.list.remove_index(2)

    @parameterized.expand(_test_params)
    def test_remove_index(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self._assert_list_size(2)
        node = self.list.remove_index(1)
        self._assert_list_size(1)
        self.assertEquals("Node2", node)
        
        self.assertEquals("Node1", self.list.head.data)
        self.assertEquals("Node1", self.list.tail.data)
        self.assertEquals("Node1", self.list.head.next.data)
        self.assertEquals("Node1", self.list.tail.next.data)

        self.list.remove_index(0)
        self._assert_empty()
        self.assertIsNone(self.list.head)
        self.assertIsNone(self.list.tail)

        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self._assert_list_size(3)
        self.list.remove_index(1)
        self._assert_list_size(2)

        self.assertEquals("Node1", self.list.head.data)
        self.assertEquals("Node3", self.list.tail.data)
        self.assertEquals("Node3", self.list.head.next.data)
        self.assertEquals("Node1", self.list.tail.next.data)
        
    @parameterized.expand(_test_params)
    def test_remove_index_head(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self.list.remove_index(0)

        self._assert_list_size(2)
        self.assertEquals("Node2", self.list.head.data)
        self.assertEquals("Node2", self.list.tail.next.data)
        self.assertEquals("Node3", self.list.head.next.data)

    @parameterized.expand(_test_params)
    def test_remove_index_tail(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self._assert_list_size(3)
        
        self.list.remove_index(2)
        self._assert_list_size(2)
        self.assertEquals("Node1", self.list.head.data)
        self.assertEquals("Node2", self.list.tail.data)
        self.assertEquals("Node1", self.list.tail.next.data)

        self.list.remove_index(0)
        self.list.remove_index(0)
        self._assert_empty()
        self.assertIsNone(self.list.head)
        self.assertIsNone(self.list.tail)

    @parameterized.expand(_test_params)
    def test_empty_list(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self._assert_list_size(1)
        self.list.clear()
        self._assert_empty()
        self.assertIsNone(self.list.head)
        self.assertIsNone(self.list.tail)

    @parameterized.expand(_test_params)
    def test_remove_empty(self, name, mode):
        self._setUp(mode)
        node = self.list.remove("Node1")
        self.assertIsNone(node)
        self._assert_empty()

    @parameterized.expand(_test_params)
    def test_remove(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self._assert_list_size(1)
        node = self.list.remove("Node1")
        self._assert_empty()
        self.assertEquals("Node1", node)

        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self._assert_list_size(3)
        node = self.list.remove("Node2")
        self._assert_list_size(2)
        self.assertEquals("Node2", node)

    @parameterized.expand(_test_params)
    def test_slice_empty(self, name, mode):
        self._setUp(mode)
        slice = self.list.slice(10)
        self.assertIsNone(slice)

    @parameterized.expand(_test_params)
    def test_slice_size_bigger_length(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self._assert_list_size(3)

        slice = self.list.slice(10)
        self.assertEquals(3, len(slice))
        self.assertTrue("Node1" in slice)
        self.assertTrue("Node2" in slice)
        self.assertTrue("Node3" in slice)

    @parameterized.expand(_test_params)
    def test_slice_rotation(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self.list.add("Node4")
        self.list.add("Node5")

        slice = self.list.slice(3)
        self.assertEquals(3, len(slice))
        self.assertTrue("Node1" in slice)
        self.assertTrue("Node2" in slice)
        self.assertTrue("Node3" in slice)

        slice = self.list.slice(3)
        self.assertEquals(3, len(slice))
        self.assertTrue("Node4" in slice)
        self.assertTrue("Node5" in slice)
        self.assertTrue("Node1" in slice)

    @parameterized.expand(_test_params)
    def test_slice_rotation_with_remove(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")
        self.list.add("Node4")
        self.list.add("Node5")

        slice = self.list.slice(3)
        self.assertEquals(3, len(slice))
        self.assertTrue("Node1" in slice)
        self.assertTrue("Node2" in slice)
        self.assertTrue("Node3" in slice)

        self.list.remove("Node4")
        
        slice = self.list.slice(3)
        self.assertEquals(3, len(slice))
        print(slice)
        self.assertTrue("Node5" in slice)
        self.assertTrue("Node1" in slice)
        self.assertTrue("Node2" in slice)

    @parameterized.expand(_test_params)
    def test_slice_rotation_with_add(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.list.add("Node2")
        self.list.add("Node3")

        slice = self.list.slice(10)
        self.assertEquals(3, len(slice))
        self.assertTrue("Node1" in slice)
        self.assertTrue("Node2" in slice)
        self.assertTrue("Node3" in slice)

        self.list.add("Node4")
        slice = self.list.slice(10)
        self.assertEqual(4, len(slice))
        self.assertTrue("Node4" in slice)

    @parameterized.expand(_test_params)
    def test_contains_empty(self, name, mode):
        self._setUp(mode)
        self.assertFalse(self.list.contains("Node1"))
        
    @parameterized.expand(_test_params)
    def test_contains(self, name, mode):
        self._setUp(mode)
        self.list.add("Node1")
        self.assertTrue(self.list.contains("Node1"))
        self.assertFalse(self.list.contains("SomeOtherNode"))
        
    def _assert_empty(self):
        self._assert_list_size(0)
        
    def _assert_list_size(self, expected):
        self.assertEquals(expected, self.list.list_size())

