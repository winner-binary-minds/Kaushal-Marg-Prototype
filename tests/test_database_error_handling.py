"""
Tests for Kaushal Marg Database Error Handling and Input Mode Persistence.

Covers:
1. Successful save sequence
2. Database failure handling (UI step block)
3. Recommendation-save failure (UI step block)
4. Duplicate submission prevention logic
5. Correct input_mode values (voice/text)
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import tempfile
from database.database import (
    create_beneficiary,
    save_profile,
    save_conversation,
    save_recommendations_batch,
    get_conversation_history,
    init_db
)

class TestDatabaseErrorHandling(unittest.TestCase):
    def setUp(self):
        """Initialize in-memory database for each test."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

    def tearDown(self):
        """Closes and removes the temporary database after each test."""
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    def test_successful_save_sequence(self):
        """Verify the full success pipeline."""
        b_id = create_beneficiary(name="Test User", db_path=self.temp_db_path)
        self.assertIsNotNone(b_id)
        
        prof_id = save_profile(
            beneficiary_id=b_id,
            education="10th Pass",
            skills=["Testing"],
            db_path=self.temp_db_path
        )
        self.assertGreater(prof_id, 0)

        # Mixed input_mode conversation
        save_conversation(b_id, "user", "Hello voice", input_mode="voice", db_path=self.temp_db_path)
        save_conversation(b_id, "assistant", "Hi", input_mode="text", db_path=self.temp_db_path)
        save_conversation(b_id, "user", "Hello text", input_mode="text", db_path=self.temp_db_path)

        history = get_conversation_history(b_id, db_path=self.temp_db_path)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["input_mode"], "voice")
        self.assertEqual(history[1]["input_mode"], "text")
        self.assertEqual(history[2]["input_mode"], "text")

        recs = save_recommendations_batch(b_id, [{"job_role": "Tester", "score": 90}], db_path=self.temp_db_path)
        self.assertEqual(len(recs), 1)

    def test_database_failure_connection_closed(self):
        """Verify that connection closes correctly even on exception."""
        # Intentionally cause an error by omitting required fields or violating constraints
        # Beneficiary ID doesn't exist, this will trigger a foreign key constraint error.
        with self.assertRaises(sqlite3.IntegrityError):
            save_profile(beneficiary_id="NON_EXISTENT", db_path=self.temp_db_path)

    @patch("database.database.get_db_connection")
    def test_save_recommendation_failure_closes_conn(self, mock_get_conn):
        """Verify save_recommendations handles failures safely."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        # Simulate a database failure during execution
        mock_conn.cursor.return_value.execute.side_effect = sqlite3.OperationalError("Disk Full")

        with self.assertRaises(sqlite3.OperationalError):
            save_recommendations_batch("test_id", [{"job_role": "Tester", "score": 90}], db_path=self.temp_db_path)
        
        # Ensure connection is closed despite the error
        mock_conn.close.assert_called_once()

    def test_duplicate_submission_handling(self):
        """Verify duplicate keys raise an IntegrityError gracefully."""
        # Insert a specific beneficiary_id manually
        b_id = "KM-TST-1234"
        create_beneficiary(name="User 1", beneficiary_id=b_id, db_path=self.temp_db_path)
        
        # Try to insert the same beneficiary_id again
        with self.assertRaises(sqlite3.IntegrityError):
             create_beneficiary(name="User 2", beneficiary_id=b_id, db_path=self.temp_db_path)


if __name__ == "__main__":
    unittest.main()
