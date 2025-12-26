"""
Unit tests for section detector and whitelist modules.
"""
import pytest
from src.sections.section_detector import detect_section, SECTION_MAP, get_all_section_page_ids
from src.sections.whitelist import WHITELIST_BY_SECTION, get_allowed_labels, is_label_allowed


class TestSectionDetector:
    """Tests for section_detector module."""
    
    def test_detect_section_prompting(self):
        """Test detection of prompting section."""
        assert detect_section("19713687690") == "prompting"
        assert detect_section("19712901293") == "prompting"
        # Note: 19712868463 moved to tagging-policy section
    
    def test_detect_section_helpdesk(self):
        """Test detection of helpdesk section."""
        assert detect_section("19700089019") == "helpdesk"
        assert detect_section("19700416664") == "helpdesk"
    
    def test_detect_section_rehab(self):
        """Test detection of rehab section."""
        assert detect_section("19711229963") == "rehab"
    
    def test_detect_section_personal(self):
        """Test detection of personal section."""
        assert detect_section("19699862097") == "personal"
    
    def test_detect_section_onboarding(self):
        """Test detection of onboarding section."""
        assert detect_section("19701137575") == "onboarding"
    
    def test_detect_section_tagging_policy(self):
        """Test detection of tagging-policy section."""
        assert detect_section("19716112385") == "tagging-policy"
        assert detect_section("19716145153") == "tagging-policy"
        assert detect_section("19713622141") == "tagging-policy"
        assert detect_section("19713622133") == "tagging-policy"
        assert detect_section("19712868463") == "tagging-policy"
        # Note: 19713687690 appears in both prompting and tagging-policy
        # detect_section returns first match (prompting)
    
    def test_detect_section_unknown_raises_error(self):
        """Test that unknown page ID raises ValueError."""
        with pytest.raises(ValueError, match="Unknown root_page_id"):
            detect_section("99999999999")
    
    def test_section_map_structure(self):
        """Test SECTION_MAP has expected structure."""
        assert "prompting" in SECTION_MAP
        assert "helpdesk" in SECTION_MAP
        assert "rehab" in SECTION_MAP
        assert "personal" in SECTION_MAP
        assert "onboarding" in SECTION_MAP
        assert "tagging-policy" in SECTION_MAP
        
        # Check all values are lists
        for section, page_ids in SECTION_MAP.items():
            assert isinstance(page_ids, list)
            assert all(isinstance(pid, str) for pid in page_ids)
    
    def test_get_all_section_page_ids(self):
        """Test getting all page IDs from all sections."""
        all_ids = get_all_section_page_ids()
        assert len(all_ids) > 0
        assert "19713687690" in all_ids
        assert "19700089019" in all_ids


class TestWhitelist:
    """Tests for whitelist module."""
    def test_whitelist_by_section_structure(self):
        """Test WHITELIST_BY_SECTION has expected structure."""
        assert "prompting" in WHITELIST_BY_SECTION
        assert "helpdesk" in WHITELIST_BY_SECTION
        assert "rehab" in WHITELIST_BY_SECTION
        assert "personal" in WHITELIST_BY_SECTION
        assert "onboarding" in WHITELIST_BY_SECTION
        assert "tagging-policy" in WHITELIST_BY_SECTION
        
        # Check all values are lists
        for section, labels in WHITELIST_BY_SECTION.items():
            assert isinstance(labels, list)
            assert all(isinstance(label, str) for label in labels)
            assert all(isinstance(label, str) for label in labels)
    
    def test_get_allowed_labels_prompting(self):
        """Test getting allowed labels for prompting section."""
        labels = get_allowed_labels("prompting")
        assert "doc-prompt-template" in labels
        assert "doc-tech" in labels
        assert "tool-rovo-agent" in labels
    
    def test_get_allowed_labels_helpdesk(self):
        """Test getting allowed labels for helpdesk section."""
        labels = get_allowed_labels("helpdesk")
        assert "domain-helpdesk-site" in labels
        assert "kb-canonical" in labels
        assert "doc-architecture" in labels
    
    def test_get_allowed_labels_rehab(self):
        """Test getting allowed labels for rehab section."""
        labels = get_allowed_labels("rehab")
        assert "domain-rehab-2-0" in labels
        assert "kb-entities-hierarchy" in labels
    
    def test_get_allowed_labels_personal(self):
        """Test getting allowed labels for personal section."""
        labels = get_allowed_labels("personal")
        assert "doc-personal" in labels
        assert len(labels) == 1
    def test_get_allowed_labels_onboarding(self):
        """Test getting allowed labels for onboarding section."""
        labels = get_allowed_labels("onboarding")
        assert "doc-onboarding" in labels
        assert "kb-overview" in labels
    
    def test_get_allowed_labels_tagging_policy(self):
        """Test getting allowed labels for tagging-policy section."""
        labels = get_allowed_labels("tagging-policy")
        assert "doc-process" in labels
        assert "doc-knowledge-base" in labels
        assert "kb-overview" in labels
    def test_is_label_allowed_true(self):
        """Test is_label_allowed returns True for allowed labels."""
        assert is_label_allowed("doc-tech", "prompting") is True
        assert is_label_allowed("kb-canonical", "helpdesk") is True
        assert is_label_allowed("doc-personal", "personal") is True
        assert is_label_allowed("doc-process", "tagging-policy") is True
        assert is_label_allowed("kb-canonical", "tagging-policy") is True
        """Test that invalid section raises KeyError."""
        with pytest.raises(KeyError, match="not found in WHITELIST_BY_SECTION"):
            get_allowed_labels("invalid_section")
    
    def test_is_label_allowed_true(self):
        """Test is_label_allowed returns True for allowed labels."""
        assert is_label_allowed("doc-tech", "prompting") is True
        assert is_label_allowed("kb-canonical", "helpdesk") is True
        assert is_label_allowed("doc-personal", "personal") is True
    
    def test_is_label_allowed_false(self):
        """Test is_label_allowed returns False for disallowed labels."""
        assert is_label_allowed("doc-personal", "prompting") is False
        assert is_label_allowed("invalid-tag", "helpdesk") is False
    
    def test_is_label_allowed_invalid_section(self):
        """Test is_label_allowed returns False for invalid section."""
        assert is_label_allowed("any-tag", "invalid_section") is False
