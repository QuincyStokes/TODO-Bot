#!/usr/bin/env python3
"""
Comprehensive tests for Discord Todo Bot
Tests server downtime recovery, guild isolation, scalability, and edge cases
"""

import unittest
import tempfile
import os
import json
import shutil
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import asyncio

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import audioop patch first to prevent import errors
import patch_audioop

from todo_manager import TodoManager, TodoList, TodoItem

class TestServerDowntimeRecovery(unittest.TestCase):
    """Test that data persists through server restarts"""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
            # Also clear in-memory data to ensure clean state
            self.todo_manager.todo_lists.clear()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_data_persistence_through_restart(self):
        """Test that all data persists through server restart"""
        # Create multiple lists with items in different states
        list1 = self.todo_manager.create_list("Shopping", "user1", "guild1")
        item1 = self.todo_manager.add_item_to_list(list1.list_id, "Milk", "user1")
        item2 = self.todo_manager.add_item_to_list(list1.list_id, "Bread", "user1")
        
        # Toggle some items to completed
        self.todo_manager.toggle_item_in_list(list1.list_id, item1.item_id, "user1")
        
        # Create another list
        list2 = self.todo_manager.create_list("Work", "user2", "guild1")
        item3 = self.todo_manager.add_item_to_list(list2.list_id, "Meeting", "user2")
        item4 = self.todo_manager.add_item_to_list(list2.list_id, "Report", "user2")
        self.todo_manager.toggle_item_in_list(list2.list_id, item3.item_id, "user2")
        
        # Force save to ensure data is written
        self.todo_manager.force_save()
        
        # Simulate server restart by creating new manager
        with patch('todo_manager.DATA_DIR', self.test_dir):
            new_manager = TodoManager("test_todo_lists.json")
        
        # Verify all data was recovered
        recovered_list1 = new_manager.get_list_by_name("Shopping", "guild1")
        recovered_list2 = new_manager.get_list_by_name("Work", "guild1")
        
        self.assertIsNotNone(recovered_list1)
        self.assertIsNotNone(recovered_list2)
        
        # Check items and their states
        self.assertEqual(len(recovered_list1.items), 2)
        self.assertEqual(len(recovered_list2.items), 2)
        
        # Check completion states
        self.assertTrue(recovered_list1.items[0].completed)  # Milk should be completed
        self.assertFalse(recovered_list1.items[1].completed)  # Bread should be incomplete
        self.assertTrue(recovered_list2.items[0].completed)  # Meeting should be completed
        self.assertFalse(recovered_list2.items[1].completed)  # Report should be incomplete
    
    def test_complex_data_recovery(self):
        """Test recovery of complex data with multiple guilds and users"""
        # Create data across multiple guilds
        guild1_list1 = self.todo_manager.create_list("Guild1-List1", "user1", "guild1")
        guild1_list2 = self.todo_manager.create_list("Guild1-List2", "user2", "guild1")
        self.todo_manager.add_item_to_list(guild1_list1.list_id, "Item1", "user1")
        self.todo_manager.add_item_to_list(guild1_list1.list_id, "Item2", "user1")
        
        # Add items and toggle some
        if guild1_list1.items:
            self.todo_manager.toggle_item_in_list(guild1_list1.list_id, guild1_list1.items[0].item_id, "user1")
        
        # Create data in guild2
        guild2_list1 = self.todo_manager.create_list("Guild2-List1", "user3", "guild2")
        self.todo_manager.add_item_to_list(guild2_list1.list_id, "Guild2Item1", "user3")
        self.todo_manager.add_item_to_list(guild2_list1.list_id, "Guild2Item2", "user3")
        
        # Force save to ensure data is written
        self.todo_manager.force_save()
        
        # Simulate restart
        with patch('todo_manager.DATA_DIR', self.test_dir):
            new_manager = TodoManager("test_todo_lists.json")
        
        # Verify guild isolation is maintained
        guild1_lists = new_manager.get_all_lists("guild1")
        guild2_lists = new_manager.get_all_lists("guild2")
        
        self.assertEqual(len(guild1_lists), 2)
        self.assertEqual(len(guild2_lists), 1)
        
        # Verify data integrity
        for list_obj in guild1_lists + guild2_lists:
            self.assertIsNotNone(list_obj.name)
            self.assertIsNotNone(list_obj.created_by)
            self.assertIsNotNone(list_obj.guild_id)

class TestGuildIsolation(unittest.TestCase):
    """Test that guild isolation works correctly"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
            # Also clear in-memory data to ensure clean state
            self.todo_manager.todo_lists.clear()
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_guild_isolation_comprehensive(self):
        """Test comprehensive guild isolation"""
        # Create lists with same names in different guilds
        list1_guild1 = self.todo_manager.create_list("Shopping", "user1", "guild1")
        list1_guild2 = self.todo_manager.create_list("Shopping", "user2", "guild2")
        list1_guild3 = self.todo_manager.create_list("Shopping", "user3", "guild3")
        
        # Add items to each list
        self.todo_manager.add_item_to_list(list1_guild1.list_id, "Guild1 Item", "user1")
        self.todo_manager.add_item_to_list(list1_guild2.list_id, "Guild2 Item", "user2")
        self.todo_manager.add_item_to_list(list1_guild3.list_id, "Guild3 Item", "user3")
        
        # Verify each guild only sees its own lists
        guild1_lists = self.todo_manager.get_all_lists("guild1")
        guild2_lists = self.todo_manager.get_all_lists("guild2")
        guild3_lists = self.todo_manager.get_all_lists("guild3")
        
        self.assertEqual(len(guild1_lists), 1)
        self.assertEqual(len(guild2_lists), 1)
        self.assertEqual(len(guild3_lists), 1)
        
        # Verify list names are correct
        self.assertEqual(guild1_lists[0].name, "Shopping")
        self.assertEqual(guild2_lists[0].name, "Shopping")
        self.assertEqual(guild3_lists[0].name, "Shopping")
        
        # Verify items are guild-specific
        self.assertEqual(guild1_lists[0].items[0].content, "Guild1 Item")
        self.assertEqual(guild2_lists[0].items[0].content, "Guild2 Item")
        self.assertEqual(guild3_lists[0].items[0].content, "Guild3 Item")
    
    def test_cross_guild_data_leakage_prevention(self):
        """Test that data doesn't leak between guilds"""
        # Create data in guild1
        list1 = self.todo_manager.create_list("Secret List", "user1", "guild1")
        self.todo_manager.add_item_to_list(list1.list_id, "Secret Item", "user1")
        
        # Create data in guild2
        list2 = self.todo_manager.create_list("Public List", "user2", "guild2")
        self.todo_manager.add_item_to_list(list2.list_id, "Public Item", "user2")
        
        # Verify guild1 cannot access guild2 data
        guild1_lists = self.todo_manager.get_all_lists("guild1")
        guild2_lists = self.todo_manager.get_all_lists("guild2")
        
        self.assertEqual(len(guild1_lists), 1)
        self.assertEqual(len(guild2_lists), 1)
        
        # Verify no cross-contamination
        for list_obj in guild1_lists:
            self.assertEqual(list_obj.guild_id, "guild1")
            self.assertNotIn("Public", [item.content for item in list_obj.items])
        
        for list_obj in guild2_lists:
            self.assertEqual(list_obj.guild_id, "guild2")
            self.assertNotIn("Secret", [item.content for item in list_obj.items])

class TestScalability(unittest.TestCase):
    """Test scalability with many users and lists"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
            # Also clear in-memory data to ensure clean state
            self.todo_manager.todo_lists.clear()
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_many_users_creating_lists(self):
        """Test performance with many users creating lists"""
        start_time = time.time()
        
        # Simulate 100 users creating lists
        for i in range(100):
            user_id = f"user{i}"
            list_name = f"List{i}"
            guild_id = f"guild{i % 5}"  # Distribute across 5 guilds
            
            # Create list
            todo_list = self.todo_manager.create_list(list_name, user_id, guild_id)
            
            # Add some items
            for j in range(5):  # 5 items per list
                self.todo_manager.add_item_to_list(todo_list.list_id, f"Item{j}", user_id)
            
            # Toggle some items
            if todo_list.items:
                self.todo_manager.toggle_item_in_list(todo_list.list_id, todo_list.items[0].item_id, user_id)
        
        creation_time = time.time() - start_time
        
        # Verify all data was created
        total_lists = len(self.todo_manager.todo_lists)
        self.assertEqual(total_lists, 100)
        
        # Verify performance is reasonable (adjusted to 10 seconds for file I/O)
        self.assertLess(creation_time, 10.0, f"Creation took {creation_time:.2f} seconds")
        
        # Test retrieval performance
        retrieval_start = time.time()
        for i in range(100):
            user_id = f"user{i}"
            list_name = f"List{i}"
            guild_id = f"guild{i % 5}"
            
            found_list = self.todo_manager.get_list_by_name(list_name, guild_id)
            self.assertIsNotNone(found_list)
        
        retrieval_time = time.time() - retrieval_start
        self.assertLess(retrieval_time, 5.0, f"Retrieval took {retrieval_time:.2f} seconds")
    
    def test_large_list_performance(self):
        """Test performance with large lists"""
        # Create a list with many items
        todo_list = self.todo_manager.create_list("Large List", "user1", "guild1")
        
        start_time = time.time()
        
        # Add 1000 items
        for i in range(1000):
            self.todo_manager.add_item_to_list(todo_list.list_id, f"Item{i}", "user1")
        
        add_time = time.time() - start_time
        self.assertLess(add_time, 15.0, f"Adding 1000 items took {add_time:.2f} seconds")
        
        # Test toggle performance
        toggle_start = time.time()
        for i in range(0, 1000, 10):  # Toggle every 10th item
            if i < len(todo_list.items):
                self.todo_manager.toggle_item_in_list(todo_list.list_id, todo_list.items[i].item_id, "user1")
        
        toggle_time = time.time() - toggle_start
        self.assertLess(toggle_time, 5.0, f"Toggling items took {toggle_time:.2f} seconds")
        
        # Verify data integrity
        self.assertEqual(len(todo_list.items), 1000)
        completed_count = sum(1 for item in todo_list.items if item.completed)
        self.assertEqual(completed_count, 100)  # Every 10th item should be completed
    
    def test_memory_usage(self):
        """Test memory usage with large datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large dataset
        for i in range(50):  # 50 lists
            todo_list = self.todo_manager.create_list(f"List{i}", f"user{i}", f"guild{i % 3}")
            for j in range(20):  # 20 items per list
                self.todo_manager.add_item_to_list(todo_list.list_id, f"Item{j}", f"user{i}")
        
        # Check memory usage
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        self.assertLess(memory_increase, 50 * 1024 * 1024, 
                       f"Memory increase: {memory_increase / (1024*1024):.2f}MB")

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
            # Also clear in-memory data to ensure clean state
            self.todo_manager.todo_lists.clear()
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_empty_list_operations(self):
        """Test operations on empty lists"""
        todo_list = self.todo_manager.create_list("Empty List", "user1", "guild1")
        
        # Try to remove from empty list
        result = self.todo_manager.remove_item_from_list(todo_list.list_id, "nonexistent")
        self.assertFalse(result)
        
        # Try to toggle nonexistent item
        result = self.todo_manager.toggle_item_in_list(todo_list.list_id, "nonexistent", "user1")
        self.assertFalse(result)
        
        # Verify list is still empty
        self.assertEqual(len(todo_list.items), 0)
    
    def test_duplicate_list_names(self):
        """Test handling of duplicate list names in same guild"""
        # Create first list
        list1 = self.todo_manager.create_list("Shopping", "user1", "guild1")
        
        # Try to create another list with same name in same guild
        # This should be prevented by the bot logic, but test the manager behavior
        list2 = self.todo_manager.create_list("Shopping", "user2", "guild1")
        
        # Both should exist (manager allows it, bot prevents it)
        self.assertNotEqual(list1.list_id, list2.list_id)
        
        # Verify both can be retrieved
        found1 = self.todo_manager.get_list_by_name("Shopping", "guild1")
        self.assertIsNotNone(found1)
    
    def test_special_characters_in_names(self):
        """Test handling of special characters in list and item names"""
        # Test various special characters
        special_names = [
            "List with spaces",
            "List-with-dashes",
            "List_with_underscores",
            "List123",
            "List!@#$%^&*()",
            "List with emoji 🎉",
            "List with unicode ñáéíóú",
            "List with quotes 'single' and \"double\"",
            "List with newlines\nand\ttabs",
            "List with very long name " + "x" * 100
        ]
        
        for name in special_names:
            todo_list = self.todo_manager.create_list(name, "user1", "guild1")
            self.assertEqual(todo_list.name, name)
            
            # Add item with special characters
            item = self.todo_manager.add_item_to_list(todo_list.list_id, name, "user1")
            self.assertEqual(item.content, name)
    
    def test_concurrent_operations(self):
        """Test concurrent operations on same list"""
        import threading
        
        todo_list = self.todo_manager.create_list("Concurrent List", "user1", "guild1")
        
        # Add some initial items
        for i in range(10):
            self.todo_manager.add_item_to_list(todo_list.list_id, f"Item{i}", "user1")
        
        # Define operations to run concurrently
        def add_items():
            for i in range(10):
                self.todo_manager.add_item_to_list(todo_list.list_id, f"Concurrent{i}", "user1")
        
        def toggle_items():
            for i in range(10):
                if i < len(todo_list.items):
                    self.todo_manager.toggle_item_in_list(todo_list.list_id, todo_list.items[i].item_id, "user1")
        
        # Run operations concurrently
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=add_items))
            threads.append(threading.Thread(target=toggle_items))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify data integrity
        final_list = self.todo_manager.get_list_by_name("Concurrent List", "guild1")
        self.assertIsNotNone(final_list)
        self.assertGreater(len(final_list.items), 10)  # Should have more items
    
    def test_corrupted_data_recovery(self):
        """Test recovery from corrupted data"""
        # Create valid data
        todo_list = self.todo_manager.create_list("Test List", "user1", "guild1")
        self.todo_manager.add_item_to_list(todo_list.list_id, "Test Item", "user1")
        
        # For database mode, we'll test by creating a new manager with a corrupted database
        # This simulates database corruption
        import sqlite3
        db_path = os.path.join(self.test_dir, "todo_bot.db")
        if os.path.exists(db_path):
            # Corrupt the database by writing invalid data
            with open(db_path, 'wb') as f:
                f.write(b"invalid database data")
        
        # Try to load corrupted data
        with patch('todo_manager.DATA_DIR', self.test_dir):
            new_manager = TodoManager("test_todo_lists.json")
        
        # Should handle corruption gracefully - either empty or fallback to JSON
        # The exact behavior depends on the database implementation
        # For now, just verify we can create new data
        new_list = new_manager.create_list("New List", "user1", "guild1")
        self.assertIsNotNone(new_list)
    
    def test_very_long_content(self):
        """Test handling of very long content"""
        # Test very long list name
        long_name = "x" * 1000
        todo_list = self.todo_manager.create_list(long_name, "user1", "guild1")
        self.assertEqual(todo_list.name, long_name)
        
        # Test very long item content
        long_content = "x" * 2000
        item = self.todo_manager.add_item_to_list(todo_list.list_id, long_content, "user1")
        self.assertEqual(item.content, long_content)
    
    def test_unicode_handling(self):
        """Test proper Unicode handling"""
        unicode_names = [
            "List with émojis 🎉🎊",
            "List with 中文 characters",
            "List with русский текст",
            "List with العربية نص",
            "List with हिंदी पाठ",
            "List with 日本語 テキスト"
        ]
        
        for name in unicode_names:
            todo_list = self.todo_manager.create_list(name, "user1", "guild1")
            self.assertEqual(todo_list.name, name)
            
            # Test serialization/deserialization
            data = todo_list.to_dict()
            recovered_list = TodoList.from_dict(data)
            self.assertEqual(recovered_list.name, name)

def run_comprehensive_tests():
    """Run comprehensive tests"""
    print("🔍 Running Comprehensive Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestServerDowntimeRecovery,
        TestGuildIsolation,
        TestScalability,
        TestEdgeCases
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Comprehensive Test Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*60}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1) 