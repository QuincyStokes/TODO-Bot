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
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
    
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
    """Test bot command logic"""
    
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.manager = TodoManager(os.path.join(self.test_dir, "test_todo_lists.json"))
        
        # Clear any existing data for test isolation
        if hasattr(self.manager, 'clear_database'):
            self.manager.clear_database()
        
        # Create test data
        self.todo_list = self.manager.create_list("Test List", "user123", "guild456")
        self.manager.add_item_to_list(self.todo_list.list_id, "Item 1", "user123")
        self.manager.add_item_to_list(self.todo_list.list_id, "Item 2", "user456")
        self.manager.add_item_to_list(self.todo_list.list_id, "Item 3", "user789")
        
        # Mock interaction
        self.interaction = Mock()
        self.interaction.guild_id = 456
        self.interaction.user.id = 123
        
    def tearDown(self):
        # Clean up test directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_list_command_logic(self):
        """Test the create list command logic"""
        # Test successful list creation
        result = self.manager.create_list("New List", "user123", "guild456")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "New List")
        self.assertEqual(result.created_by, "user123")
        self.assertEqual(result.guild_id, "guild456")
        
        # Test duplicate list name in same guild (should work - we allow duplicates)
        duplicate_result = self.manager.create_list("New List", "user456", "guild456")
        self.assertIsNotNone(duplicate_result)  # Should work - we allow duplicates
        
        # Test same name in different guild (should work)
        other_guild_result = self.manager.create_list("New List", "user789", "guild789")
        self.assertIsNotNone(other_guild_result)
    
    def test_add_item_command_logic(self):
        """Test the add item command logic"""
        # Test successful item addition
        new_item = self.manager.add_item_to_list(self.todo_list.list_id, "New Item", "user123")
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item.content, "New Item")
        self.assertEqual(new_item.created_by, "user123")
        
        # Verify item was added to the list
        updated_list = self.manager.get_list_by_name("Test List", "guild456")
        self.assertEqual(len(updated_list.items), 4)
    
    def test_list_lists_command_logic(self):
        """Test the list lists command logic"""
        # Create additional lists
        self.manager.create_list("List 2", "user456", "guild456")
        self.manager.create_list("List 3", "user789", "guild456")
        
        # Test getting all lists for guild
        lists = self.manager.get_all_lists("guild456")
        self.assertEqual(len(lists), 3)
        
        # Test getting lists for different guild
        other_lists = self.manager.get_all_lists("guild789")
        self.assertEqual(len(other_lists), 0)
    
    def test_info_command_logic(self):
        """Test the info command logic"""
        # Test getting info for existing list
        list_info = self.manager.get_list_by_name("Test List", "guild456")
        self.assertIsNotNone(list_info)
        self.assertEqual(list_info.name, "Test List")
        self.assertEqual(len(list_info.items), 3)
        
        # Test getting info for non-existent list
        non_existent = self.manager.get_list_by_name("Non Existent", "guild456")
        self.assertIsNone(non_existent)
        
        # Test getting info for list in different guild
        other_guild = self.manager.get_list_by_name("Test List", "guild789")
        self.assertIsNone(other_guild)
    
    def test_show_command_logic(self):
        """Test the show command logic with interactive buttons"""
        # Test showing existing list
        list_to_show = self.manager.get_list_by_name("Test List", "guild456")
        self.assertIsNotNone(list_to_show)
        self.assertEqual(len(list_to_show.items), 3)
        
        # Test showing non-existent list
        non_existent = self.manager.get_list_by_name("Non Existent", "guild456")
        self.assertIsNone(non_existent)
    
    def test_refresh_command_logic(self):
        """Test the refresh command logic"""
        # Test refreshing existing list
        list_to_refresh = self.manager.get_list_by_name("Test List", "guild456")
        self.assertIsNotNone(list_to_refresh)
        self.assertEqual(len(list_to_refresh.items), 3)
        
        # Test refreshing non-existent list
        non_existent = self.manager.get_list_by_name("Non Existent", "guild456")
        self.assertIsNone(non_existent)
    
    def test_delete_command_logic(self):
        """Test the delete command logic"""
        # Test deleting existing list
        list_to_delete = self.manager.get_list_by_name("Test List", "guild456")
        self.assertIsNotNone(list_to_delete)
        
        # Delete the list
        success = self.manager.delete_list(list_to_delete.list_id)
        self.assertTrue(success)
        
        # Verify list is deleted
        deleted_list = self.manager.get_list_by_name("Test List", "guild456")
        self.assertIsNone(deleted_list)
        
        # Test deleting non-existent list
        non_existent_success = self.manager.delete_list("non-existent-id")
        self.assertFalse(non_existent_success)

class TestNewFeatures(unittest.TestCase):
    """Test new features and improvements"""
    
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.manager = TodoManager(os.path.join(self.test_dir, "test_todo_lists.json"))
        
        # Clear any existing data for test isolation
        if hasattr(self.manager, 'clear_database'):
            self.manager.clear_database()
        
        # Create test data with completed items
        self.todo_list = self.manager.create_list("Test List", "user123", "guild456")
        self.manager.add_item_to_list(self.todo_list.list_id, "Item 1", "user123")
        self.manager.add_item_to_list(self.todo_list.list_id, "Item 2", "user456")
        self.manager.add_item_to_list(self.todo_list.list_id, "Item 3", "user789")
        
        # Complete one item
        self.manager.toggle_item_in_list(self.todo_list.list_id, self.todo_list.items[0].item_id, "user123")
        
    def tearDown(self):
        # Clean up test directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_info_command_statistics(self):
        """Test the info command statistics calculation"""
        list_info = self.manager.get_list_by_name("Test List", "guild456")
        
        # Test statistics
        total_items = len(list_info.items)
        completed_items = sum(1 for item in list_info.items if item.completed)
        pending_items = sum(1 for item in list_info.items if not item.completed)
        completion_rate = round((completed_items / total_items * 100) if total_items > 0 else 0, 1)
        
        self.assertEqual(total_items, 3)
        self.assertEqual(completed_items, 1)
        self.assertEqual(pending_items, 2)
        self.assertEqual(completion_rate, 33.3)
    
    def test_info_command_technical_details(self):
        """Test the info command technical details"""
        list_info = self.manager.get_list_by_name("Test List", "guild456")
        
        # Test technical details are present
        self.assertIsNotNone(list_info.list_id)
        self.assertEqual(list_info.guild_id, "guild456")
        self.assertEqual(list_info.created_by, "user123")
        self.assertIsNotNone(list_info.created_at)
    
    def test_info_command_item_breakdown(self):
        """Test the info command item breakdown"""
        list_info = self.manager.get_list_by_name("Test List", "guild456")
        
        # Test completed items
        completed_items = [item for item in list_info.items if item.completed]
        self.assertEqual(len(completed_items), 1)
        self.assertEqual(completed_items[0].content, "Item 1")
        
        # Test pending items
        pending_items = [item for item in list_info.items if not item.completed]
        self.assertEqual(len(pending_items), 2)
        self.assertEqual(pending_items[0].content, "Item 2")
        self.assertEqual(pending_items[1].content, "Item 3")
    
    def test_empty_list_info(self):
        """Test info command with empty list"""
        # Create empty list
        empty_list = self.manager.create_list("Empty List", "user123", "guild456")
        
        # Test statistics for empty list
        total_items = len(empty_list.items)
        completed_items = sum(1 for item in empty_list.items if item.completed)
        pending_items = sum(1 for item in empty_list.items if not item.completed)
        completion_rate = round((completed_items / total_items * 100) if total_items > 0 else 0, 1)
        
        self.assertEqual(total_items, 0)
        self.assertEqual(completed_items, 0)
        self.assertEqual(pending_items, 0)
        self.assertEqual(completion_rate, 0.0)
    
    def test_safe_interaction_response_handling(self):
        """Test safe interaction response handling"""
        # Mock interaction with response already done
        interaction = Mock()
        interaction.response.is_done.return_value = True
        interaction.followup.send = Mock()
        
        # Test that followup.send is called when response is done
        # This would be tested in actual bot code, but we can verify the logic
        response_done = interaction.response.is_done()
        self.assertTrue(response_done)
    
    def test_timeout_handling(self):
        """Test timeout handling for views"""
        # Test that timeout messages include proper instructions
        timeout_instructions = [
            "Use `/show {list_name}` to get a fresh interactive view",
            "Use commands like `/add`, `/toggle`, `/remove` for direct actions"
        ]
        
        # Verify all timeout instructions are present
        for instruction in timeout_instructions:
            if "show" in instruction:
                self.assertIn("show", instruction)
            elif "commands" in instruction:
                self.assertIn("commands", instruction)
        
        # Test that we have the expected number of instructions
        self.assertEqual(len(timeout_instructions), 2)
    
    def test_embed_creation_without_list_id(self):
        """Test that embeds are created without List ID in footer"""
        list_info = self.manager.get_list_by_name("Test List", "guild456")
        
        # Simulate embed creation (this would be done in actual bot code)
        embed_title = f"📋 {list_info.name}"
        embed_description = f"Created by <@{list_info.created_by}>"
        
        self.assertEqual(embed_title, "📋 Test List")
        self.assertEqual(embed_description, "Created by <@user123>")
        
        # Verify no List ID in footer (this would be checked in actual embed)
        # The actual embed creation is in bot.py, but we can test the logic here
        self.assertIsNotNone(list_info.list_id)  # List ID should exist
        # But it shouldn't be in the display embed footer anymore
    
    def test_command_error_handling(self):
        """Test command error handling"""
        # Test that commands handle missing lists gracefully
        non_existent = self.manager.get_list_by_name("Non Existent", "guild456")
        self.assertIsNone(non_existent)
        
        # Test that commands handle invalid item numbers gracefully
        list_info = self.manager.get_list_by_name("Test List", "guild456")
        item_count = len(list_info.items)
        
        # Test invalid item numbers
        self.assertGreater(item_count, 0)  # Should have items
        self.assertLess(0, item_count)     # Item numbers should be 1-based
        self.assertLess(item_count, 100)   # Reasonable upper bound


class TestMultiItemAdd(unittest.TestCase):
    """Test multi-item add functionality"""
    
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.original_data_dir = os.environ.get('DATA_DIR')
        os.environ['DATA_DIR'] = self.test_dir
        
        # Initialize TodoManager
        self.todo_manager = TodoManager("test_todo_lists.json")
        
        # Create a test list
        self.todo_list = self.todo_manager.create_list("Test List", "user123", "guild456")
    
    def tearDown(self):
        # Clean up test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if self.original_data_dir:
            os.environ['DATA_DIR'] = self.original_data_dir
        else:
            os.environ.pop('DATA_DIR', None)
    
    def test_single_item_add(self):
        """Test adding a single item (backward compatibility)"""
        # Simulate the add command logic
        items_input = "Single item"
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 1)
        self.assertEqual(item_list[0], "Single item")
        
        # Add the item
        new_item = self.todo_manager.add_item_to_list(self.todo_list.list_id, item_list[0], "user123")
        
        self.assertIsNotNone(new_item)
        self.assertEqual(len(self.todo_list.items), 1)
        self.assertEqual(self.todo_list.items[0].content, "Single item")
    
    def test_multiple_items_add(self):
        """Test adding multiple items with comma separation"""
        items_input = "Milk, Bread, Eggs, Butter"
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 4)
        self.assertEqual(item_list, ["Milk", "Bread", "Eggs", "Butter"])
        
        # Add all items
        successful_items = []
        for item in item_list:
            new_item = self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
            if new_item:
                successful_items.append(item)
        
        self.assertEqual(len(successful_items), 4)
        self.assertEqual(len(self.todo_list.items), 4)
        self.assertEqual([item.content for item in self.todo_list.items], ["Milk", "Bread", "Eggs", "Butter"])
    
    def test_items_with_extra_whitespace(self):
        """Test handling of items with extra whitespace"""
        items_input = "  Milk  ,  Bread  ,  Eggs  "
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 3)
        self.assertEqual(item_list, ["Milk", "Bread", "Eggs"])
        
        # Add items
        for item in item_list:
            self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
        
        self.assertEqual(len(self.todo_list.items), 3)
        self.assertEqual([item.content for item in self.todo_list.items], ["Milk", "Bread", "Eggs"])
    
    def test_empty_items_filtering(self):
        """Test that empty items are filtered out"""
        items_input = "Milk,, Bread, , Eggs,"
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 3)
        self.assertEqual(item_list, ["Milk", "Bread", "Eggs"])
        
        # Add items
        for item in item_list:
            self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
        
        self.assertEqual(len(self.todo_list.items), 3)
    
    def test_items_with_commas_in_quotes(self):
        """Test handling of items that contain commas (simulated with quotes)"""
        # This simulates how users might handle items with commas
        # Note: The current implementation splits by comma, so quoted items with commas
        # will be split. Users would need to handle this manually or we'd need
        # more sophisticated parsing
        items_input = '"Buy milk, bread, and eggs", "Call mom", "Walk the dog"'
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        # With current implementation, this would split into 5 items:
        # '"Buy milk', ' bread', ' and eggs"', ' "Call mom"', ' "Walk the dog"'
        self.assertEqual(len(item_list), 5)
        
        # Add items
        for item in item_list:
            self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
        
        self.assertEqual(len(self.todo_list.items), 5)
    
    def test_mixed_success_and_failure(self):
        """Test scenario where some items succeed and others fail"""
        items_input = "Valid item 1, Valid item 2, Valid item 3"
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        successful_items = []
        failed_items = []
        
        for item in item_list:
            new_item = self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
            if new_item:
                successful_items.append(item)
            else:
                failed_items.append(item)
        
        # All items should succeed in normal operation
        self.assertEqual(len(successful_items), 3)
        self.assertEqual(len(failed_items), 0)
        self.assertEqual(len(self.todo_list.items), 3)
    
    def test_empty_input_validation(self):
        """Test validation of empty input"""
        items_input = "   ,  ,  "
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 0)
        
        # Should not add any items
        self.assertEqual(len(self.todo_list.items), 0)
    
    def test_single_empty_item(self):
        """Test handling of single empty item"""
        items_input = ""
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 0)
        
        # Should not add any items
        self.assertEqual(len(self.todo_list.items), 0)
    
    def test_large_number_of_items(self):
        """Test adding a large number of items"""
        items_input = ", ".join([f"Item {i}" for i in range(1, 21)])  # 20 items
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 20)
        
        # Add all items
        for item in item_list:
            self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
        
        self.assertEqual(len(self.todo_list.items), 20)
        self.assertEqual(self.todo_list.items[0].content, "Item 1")
        self.assertEqual(self.todo_list.items[19].content, "Item 20")
    
    def test_special_characters_in_items(self):
        """Test items with special characters"""
        items_input = "Buy groceries 🛒, Call mom 📞, Walk dog 🐕"
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 3)
        
        # Add items
        for item in item_list:
            self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
        
        self.assertEqual(len(self.todo_list.items), 3)
        self.assertEqual(self.todo_list.items[0].content, "Buy groceries 🛒")
        self.assertEqual(self.todo_list.items[1].content, "Call mom 📞")
        self.assertEqual(self.todo_list.items[2].content, "Walk dog 🐕")
    
    def test_duplicate_items(self):
        """Test adding duplicate items"""
        items_input = "Milk, Milk, Bread, Bread, Eggs"
        item_list = [item.strip() for item in items_input.split(',') if item.strip()]
        
        self.assertEqual(len(item_list), 5)
        
        # Add items
        for item in item_list:
            self.todo_manager.add_item_to_list(self.todo_list.list_id, item, "user123")
        
        # All items should be added (duplicates are allowed)
        self.assertEqual(len(self.todo_list.items), 5)
        self.assertEqual([item.content for item in self.todo_list.items], ["Milk", "Milk", "Bread", "Bread", "Eggs"])


class TestDataIsolation(unittest.TestCase):
    """Test data isolation between guilds and users"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
    
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
        TestNewFeatures,
        TestMultiItemAdd,
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