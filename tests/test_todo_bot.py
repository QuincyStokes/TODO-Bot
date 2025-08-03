#!/usr/bin/env python3
"""
Test suite for Discord Todo Bot
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, MagicMock
import sys
import asyncio

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import audioop patch first to prevent import errors
import patch_audioop

from todo_manager import TodoManager, TodoList, TodoItem
import discord
from discord import app_commands
from discord.ext import commands

class TestTodoItem(unittest.TestCase):
    """Test TodoItem functionality"""
    
    def setUp(self):
        self.item = TodoItem("Test item", "user123")
    
    def test_item_creation(self):
        """Test TodoItem creation"""
        self.assertEqual(self.item.content, "Test item")
        self.assertEqual(self.item.created_by, "user123")
        self.assertFalse(self.item.completed)
        self.assertIsNone(self.item.completed_by)
        self.assertIsNotNone(self.item.item_id)
        self.assertIsNotNone(self.item.created_at)
    
    def test_item_to_dict(self):
        """Test TodoItem serialization"""
        data = self.item.to_dict()
        self.assertEqual(data['content'], "Test item")
        self.assertEqual(data['created_by'], "user123")
        self.assertFalse(data['completed'])
        self.assertIn('item_id', data)
        self.assertIn('created_at', data)
    
    def test_item_from_dict(self):
        """Test TodoItem deserialization"""
        original_data = self.item.to_dict()
        new_item = TodoItem.from_dict(original_data)
        self.assertEqual(new_item.content, self.item.content)
        self.assertEqual(new_item.created_by, self.item.created_by)
        self.assertEqual(new_item.completed, self.item.completed)
        self.assertEqual(new_item.item_id, self.item.item_id)

class TestTodoList(unittest.TestCase):
    """Test TodoList functionality"""
    
    def setUp(self):
        self.todo_list = TodoList("Test List", "user123", "guild456")
    
    def test_list_creation(self):
        """Test TodoList creation"""
        self.assertEqual(self.todo_list.name, "Test List")
        self.assertEqual(self.todo_list.created_by, "user123")
        self.assertEqual(self.todo_list.guild_id, "guild456")
        self.assertEqual(len(self.todo_list.items), 0)
        self.assertIsNotNone(self.todo_list.list_id)
        self.assertIsNotNone(self.todo_list.created_at)
    
    def test_add_item(self):
        """Test adding items to list"""
        item = self.todo_list.add_item("New item", "user456")
        self.assertEqual(len(self.todo_list.items), 1)
        self.assertEqual(item.content, "New item")
        self.assertEqual(item.created_by, "user456")
    
    def test_remove_item(self):
        """Test removing items from list"""
        item = self.todo_list.add_item("Test item", "user123")
        self.assertTrue(self.todo_list.remove_item(item.item_id))
        self.assertEqual(len(self.todo_list.items), 0)
    
    def test_toggle_item(self):
        """Test toggling item completion"""
        item = self.todo_list.add_item("Test item", "user123")
        self.assertFalse(item.completed)
        
        # Toggle to completed
        self.assertTrue(self.todo_list.toggle_item(item.item_id, "user456"))
        self.assertTrue(item.completed)
        self.assertEqual(item.completed_by, "user456")
        self.assertIsNotNone(item.completed_at)
        
        # Toggle back to incomplete
        self.assertTrue(self.todo_list.toggle_item(item.item_id, "user789"))
        self.assertFalse(item.completed)
        self.assertIsNone(item.completed_by)
        self.assertIsNone(item.completed_at)
    
    def test_list_to_dict(self):
        """Test TodoList serialization"""
        self.todo_list.add_item("Test item", "user123")
        data = self.todo_list.to_dict()
        self.assertEqual(data['name'], "Test List")
        self.assertEqual(data['created_by'], "user123")
        self.assertEqual(data['guild_id'], "guild456")
        self.assertEqual(len(data['items']), 1)
    
    def test_list_from_dict(self):
        """Test TodoList deserialization"""
        original_data = self.todo_list.to_dict()
        new_list = TodoList.from_dict(original_data)
        self.assertEqual(new_list.name, self.todo_list.name)
        self.assertEqual(new_list.created_by, self.todo_list.created_by)
        self.assertEqual(new_list.guild_id, self.todo_list.guild_id)

class TestTodoManager(unittest.TestCase):
    """Test TodoManager functionality"""
    
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_todo_lists.json")
        
        # Patch the DATA_DIR to use our test directory
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
    
    def tearDown(self):
        # Clean up test directory
        shutil.rmtree(self.test_dir)
    
    def test_manager_creation(self):
        """Test TodoManager creation"""
        self.assertEqual(len(self.todo_manager.todo_lists), 0)
        self.assertTrue(os.path.exists(self.test_dir))
    
    def test_create_list(self):
        """Test creating a todo list"""
        todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
        self.assertEqual(todo_list.name, "Test List")
        self.assertEqual(todo_list.created_by, "user123")
        self.assertEqual(todo_list.guild_id, "guild456")
        self.assertIn(todo_list.list_id, self.todo_manager.todo_lists)
    
    def test_get_list_by_name(self):
        """Test getting list by name within guild"""
        # Create lists in different guilds
        list1 = self.todo_manager.create_list("Shopping", "user123", "guild1")
        list2 = self.todo_manager.create_list("Shopping", "user456", "guild2")
        
        # Should only find list in guild1
        found_list = self.todo_manager.get_list_by_name("Shopping", "guild1")
        self.assertEqual(found_list.list_id, list1.list_id)
        
        # Should not find list in guild3
        not_found = self.todo_manager.get_list_by_name("Shopping", "guild3")
        self.assertIsNone(not_found)
    
    def test_get_all_lists(self):
        """Test getting all lists for a guild"""
        # Create lists in different guilds
        list1 = self.todo_manager.create_list("List1", "user123", "guild1")
        list2 = self.todo_manager.create_list("List2", "user456", "guild1")
        list3 = self.todo_manager.create_list("List3", "user789", "guild2")
        
        # Verify lists were created
        self.assertIn(list1.list_id, self.todo_manager.todo_lists)
        self.assertIn(list2.list_id, self.todo_manager.todo_lists)
        self.assertIn(list3.list_id, self.todo_manager.todo_lists)
        
        guild1_lists = self.todo_manager.get_all_lists("guild1")
        self.assertEqual(len(guild1_lists), 2)
        
        guild2_lists = self.todo_manager.get_all_lists("guild2")
        self.assertEqual(len(guild2_lists), 1)
        
        guild3_lists = self.todo_manager.get_all_lists("guild3")
        self.assertEqual(len(guild3_lists), 0)
    
    def test_add_item_to_list(self):
        """Test adding items to a list"""
        todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
        item = self.todo_manager.add_item_to_list(todo_list.list_id, "New item", "user456")
        
        self.assertIsNotNone(item)
        self.assertEqual(item.content, "New item")
        self.assertEqual(item.created_by, "user456")
        self.assertEqual(len(todo_list.items), 1)
    
    def test_remove_item_from_list(self):
        """Test removing items from a list"""
        todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
        item = self.todo_manager.add_item_to_list(todo_list.list_id, "Test item", "user123")
        
        self.assertTrue(self.todo_manager.remove_item_from_list(todo_list.list_id, item.item_id))
        self.assertEqual(len(todo_list.items), 0)
    
    def test_toggle_item_in_list(self):
        """Test toggling item completion in a list"""
        todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
        item = self.todo_manager.add_item_to_list(todo_list.list_id, "Test item", "user123")
        
        # Toggle to completed
        self.assertTrue(self.todo_manager.toggle_item_in_list(todo_list.list_id, item.item_id, "user456"))
        self.assertTrue(item.completed)
        self.assertEqual(item.completed_by, "user456")
        
        # Toggle back to incomplete
        self.assertTrue(self.todo_manager.toggle_item_in_list(todo_list.list_id, item.item_id, "user789"))
        self.assertFalse(item.completed)
        self.assertIsNone(item.completed_by)
    
    def test_delete_list(self):
        """Test deleting a todo list"""
        todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
        self.assertIn(todo_list.list_id, self.todo_manager.todo_lists)
        
        self.assertTrue(self.todo_manager.delete_list(todo_list.list_id))
        self.assertNotIn(todo_list.list_id, self.todo_manager.todo_lists)
    
    def test_data_persistence(self):
        """Test that data persists between manager instances"""
        # Create data with first manager
        todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
        self.todo_manager.add_item_to_list(todo_list.list_id, "Test item", "user123")
        
        # Force save to ensure data is written
        self.todo_manager.force_save()
        
        # Create new manager instance (should load existing data)
        with patch('todo_manager.DATA_DIR', self.test_dir):
            new_manager = TodoManager("test_todo_lists.json")
        
        # Verify data was loaded
        loaded_list = new_manager.get_list_by_name("Test List", "guild456")
        self.assertIsNotNone(loaded_list)
        self.assertEqual(len(loaded_list.items), 1)
        self.assertEqual(loaded_list.items[0].content, "Test item")

class TestBotCommands(unittest.TestCase):
    """Test bot command functionality"""
    
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Mock the bot and interaction
        self.bot = Mock()
        self.interaction = Mock()
        self.interaction.guild_id = 123456789
        self.interaction.user.id = 987654321
        self.interaction.response.send_message = Mock()
        self.interaction.response.edit_message = Mock()
        self.interaction.channel.send = Mock()
        
        # Patch the todo manager
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            self.bot.todo_manager = self.todo_manager
    
    def tearDown(self):
        # Clean up test directory
        shutil.rmtree(self.test_dir)
    
    def test_create_list_command_logic(self):
        """Test the create list command logic"""
        # Test successful creation
        self.interaction.guild_id = 123456789
        self.interaction.user.id = 987654321
        
        # Test the logic directly
        guild_id = str(self.interaction.guild_id)
        name = "Test List"
        
        # Check if list already exists
        existing_list = self.todo_manager.get_list_by_name(name, guild_id)
        self.assertIsNone(existing_list)
        
        # Create new list
        todo_list = self.todo_manager.create_list(name, str(self.interaction.user.id), guild_id)
        self.assertIsNotNone(todo_list)
        self.assertEqual(todo_list.name, name)
        self.assertEqual(todo_list.created_by, str(self.interaction.user.id))
        self.assertEqual(todo_list.guild_id, guild_id)
    
    def test_add_item_command_logic(self):
        """Test the add item command logic"""
        # Create a list first
        todo_list = self.todo_manager.create_list("Test List", "987654321", "123456789")
        
        # Test adding item
        guild_id = str(self.interaction.guild_id)
        list_name = "Test List"
        item_content = "New item"
        
        # Find the list in this guild
        found_list = self.todo_manager.get_list_by_name(list_name, guild_id)
        self.assertIsNotNone(found_list)
        
        # Add item
        new_item = self.todo_manager.add_item_to_list(found_list.list_id, item_content, str(self.interaction.user.id))
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item.content, item_content)
    
    def test_list_lists_command_logic(self):
        """Test the list lists command logic"""
        # Create some lists
        self.todo_manager.create_list("List1", "987654321", "123456789")
        self.todo_manager.create_list("List2", "987654321", "123456789")
        
        # Test listing
        guild_id = str(self.interaction.guild_id)
        todo_lists = self.todo_manager.get_all_lists(guild_id)
        
        self.assertEqual(len(todo_lists), 2)
        self.assertEqual(todo_lists[0].name, "List1")
        self.assertEqual(todo_lists[1].name, "List2")

class TestDataIsolation(unittest.TestCase):
    """Test data isolation between guilds and users"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_guild_isolation(self):
        """Test that lists are isolated by guild"""
        # Create lists in different guilds
        list1 = self.todo_manager.create_list("Shopping", "user1", "guild1")
        list2 = self.todo_manager.create_list("Shopping", "user2", "guild2")
        
        # Lists should be separate
        self.assertNotEqual(list1.list_id, list2.list_id)
        
        # Should only find lists in correct guild
        found1 = self.todo_manager.get_list_by_name("Shopping", "guild1")
        found2 = self.todo_manager.get_list_by_name("Shopping", "guild2")
        
        self.assertEqual(found1.list_id, list1.list_id)
        self.assertEqual(found2.list_id, list2.list_id)
        self.assertIsNone(self.todo_manager.get_list_by_name("Shopping", "guild3"))
    
    def test_user_permissions(self):
        """Test user permission checks"""
        # Create list with user1
        todo_list = self.todo_manager.create_list("Test List", "user1", "guild1")
        
        # Add item with user2 (should work)
        item = self.todo_manager.add_item_to_list(todo_list.list_id, "Item by user2", "user2")
        self.assertIsNotNone(item)
        
        # Toggle item with user3 (should work)
        success = self.todo_manager.toggle_item_in_list(todo_list.list_id, item.item_id, "user3")
        self.assertTrue(success)
        
        # List should be accessible by all users in the guild
        found_list = self.todo_manager.get_list_by_name("Test List", "guild1")
        self.assertIsNotNone(found_list)

def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestTodoItem,
        TestTodoList,
        TestTodoManager,
        TestBotCommands,
        TestDataIsolation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Test Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 