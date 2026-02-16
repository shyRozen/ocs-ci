"""
Parse JUnit XML test results into structured TestResult objects.

Uses the junitparser library (already an ocs-ci dependency).
"""

import logging
import tempfile
import os
from typing import Optional
from xml.etree import ElementTree

from ocs_ci.utility.log_analysis.exceptions import JUnitParseError
from ocs_ci.utility.log_analysis.models import TestResult, TestStatus

logger = logging.getLogger(__name__)


class JUnitResultParser:
    """Parse JUnit XML files produced by ocs-ci pytest runs."""

    def parse_from_string(self, xml_content: str) -> list:
        """
        Parse JUnit XML from a string.

        Args:
            xml_content: JUnit XML as a string

        Returns:
            list[TestResult]: Parsed test results
        """
        try:
            root = ElementTree.fromstring(xml_content)
        except ElementTree.ParseError as e:
            raise JUnitParseError(f"Failed to parse JUnit XML: {e}")

        return self._parse_tree(root)

    def parse_from_file(self, file_path: str) -> list:
        """
        Parse JUnit XML from a file.

        Args:
            file_path: Path to JUnit XML file

        Returns:
            list[TestResult]: Parsed test results
        """
        try:
            tree = ElementTree.parse(file_path)
            root = tree.getroot()
        except (ElementTree.ParseError, IOError) as e:
            raise JUnitParseError(f"Failed to parse JUnit XML from {file_path}: {e}")

        return self._parse_tree(root)

    def _parse_tree(self, root) -> list:
        """Parse an ElementTree root into TestResult objects."""
        results = []
        self.suite_timestamp = ""

        # Handle both <testsuites><testsuite>... and <testsuite>... formats
        if root.tag == "testsuites":
            testsuites = root.findall("testsuite")
        elif root.tag == "testsuite":
            testsuites = [root]
        else:
            raise JUnitParseError(f"Unexpected root element: {root.tag}")

        for testsuite in testsuites:
            # Extract timestamp from first testsuite
            if not self.suite_timestamp:
                self.suite_timestamp = testsuite.get("timestamp", "")
            # Extract testsuite-level properties
            suite_props = self._extract_properties(testsuite)

            for testcase in testsuite.findall("testcase"):
                result = self._parse_testcase(testcase, suite_props)
                results.append(result)

        logger.info(
            f"Parsed {len(results)} test results: "
            f"{sum(1 for r in results if r.status == TestStatus.PASSED)} passed, "
            f"{sum(1 for r in results if r.status == TestStatus.FAILED)} failed, "
            f"{sum(1 for r in results if r.status == TestStatus.ERROR)} error, "
            f"{sum(1 for r in results if r.status == TestStatus.SKIPPED)} skipped"
        )

        return results

    def _parse_testcase(self, testcase, suite_props: dict) -> TestResult:
        """Parse a single <testcase> element."""
        classname = testcase.get("classname", "")
        name = testcase.get("name", "")
        duration = float(testcase.get("time", 0))

        # Determine status and extract details
        status = TestStatus.PASSED
        traceback = None
        skip_reason = None

        failure = testcase.find("failure")
        if failure is not None:
            status = TestStatus.FAILED
            traceback = failure.text or ""
            msg = failure.get("message", "")
            if msg and not traceback:
                traceback = msg

        error = testcase.find("error")
        if error is not None:
            status = TestStatus.ERROR
            traceback = error.text or ""
            msg = error.get("message", "")
            if msg and not traceback:
                traceback = msg

        skipped = testcase.find("skipped")
        if skipped is not None:
            status = TestStatus.SKIPPED
            skip_reason = skipped.get("message", "")
            if not skip_reason:
                skip_reason = skipped.text or ""

        # Extract test-case level properties (squad, polarion_id)
        case_props = self._extract_properties(testcase)
        squad = case_props.get("squad")
        polarion_id = case_props.get("polarion-testcase-id")

        # Construct log path from suite properties if available
        log_path = None
        logs_url = suite_props.get("logs-url")
        run_id = suite_props.get("run_id")
        if logs_url and run_id:
            # Build the per-test log path from classname
            test_path = classname.replace(".", "/")
            test_module = test_path.rsplit("/", 1)
            if len(test_module) == 2:
                module_path = test_module[0]
                # Remove the 'tests.' prefix to match directory structure
                if module_path.startswith("tests/"):
                    pass
                log_path = (
                    f"{logs_url.rstrip('/')}/ocs-ci-logs-{run_id}"
                    f"/{module_path}/{name}/logs"
                )

        return TestResult(
            classname=classname,
            name=name,
            status=status,
            duration=duration,
            traceback=traceback,
            skip_reason=skip_reason,
            squad=squad,
            polarion_id=polarion_id,
            log_path=log_path,
        )

    def _extract_properties(self, element) -> dict:
        """Extract <property> elements from a testcase or testsuite."""
        props = {}
        properties_elem = element.find("properties")
        if properties_elem is not None:
            for prop in properties_elem.findall("property"):
                name = prop.get("name", "")
                value = prop.get("value", "")
                if name:
                    props[name] = value
        return props
