#!/usr/bin/env python3
"""
RLS lint check for undeclared user-owned models.

This script validates that all models with owner_id fields inherit from UserScopedBase
for proper RLS enforcement. It's designed to be run as part of CI/CD pipelines and
pre-commit hooks to ensure RLS compliance.
"""

import argparse
import ast
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RLSModelLinter:
    """Linter for RLS model compliance."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.userscoped_models: set[str] = set()
        self.models_with_owner_id: set[str] = set()

    def check_file(self, file_path: Path) -> None:
        """Check a single Python file for RLS compliance."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            self._analyze_ast(tree, file_path)

        except Exception as e:
            self.errors.append(f"Error parsing {file_path}: {e}")

    def _analyze_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Analyze AST for RLS model compliance."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_class_def(node, file_path)

    def _check_class_def(self, class_node: ast.ClassDef, file_path: Path) -> None:
        """Check a class definition for RLS compliance."""
        # Skip non-model classes
        if not self._is_model_class(class_node):
            return

        class_name = class_node.name
        has_owner_id = False
        inherits_userscoped = False

        # Check for owner_id field
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign):
                if hasattr(node.target, "id") and node.target.id == "owner_id":
                    has_owner_id = True
                    break

        # Check inheritance from UserScopedBase
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "UserScopedBase":
                inherits_userscoped = True
                break
            elif isinstance(base, ast.Attribute):
                if base.attr == "UserScopedBase":
                    inherits_userscoped = True
                    break

        # Record findings
        if inherits_userscoped:
            self.userscoped_models.add(class_name)

        if has_owner_id:
            self.models_with_owner_id.add(class_name)

        # Check compliance (skip UserScopedBase itself as it defines the field)
        if not inherits_userscoped and class_name != "UserScopedBase":
            error_msg = (
                f"Model '{class_name}' in {file_path} has 'owner_id' field "
                f"but does not inherit from UserScopedBase. "
                f"This violates RLS compliance requirements."
            )
            self.errors.append(error_msg)

    def _is_model_class(self, class_node: ast.ClassDef) -> bool:
        """Check if a class is a database model (not a Pydantic schema)."""
        # Only check classes that have table=True decorator or inherit from UserScopedBase
        # Skip all other SQLModel classes as they are schemas, not database tables

        # Look for table=True in class decorators or keywords
        for decorator in class_node.decorator_list:
            if isinstance(decorator, ast.Call):
                if (
                    isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "table"
                ):
                    for keyword in decorator.keywords:
                        if keyword.arg == "value" and isinstance(
                            keyword.value, ast.Constant
                        ):
                            if keyword.value.value is True:
                                return True
                elif isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "table":
                        for keyword in decorator.keywords:
                            if keyword.arg == "value" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                if keyword.value.value is True:
                                    return True
            elif isinstance(decorator, ast.Name):
                if decorator.id == "table":
                    return True

        # Check for UserScopedBase inheritance (these are always database models)
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                if base.id == "UserScopedBase":
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr == "UserScopedBase":
                    return True

        return False

    def check_directory(self, directory: Path) -> None:
        """Check all Python files in a directory for RLS compliance."""
        if not directory.exists():
            self.errors.append(f"Directory does not exist: {directory}")
            return

        python_files = list(directory.rglob("*.py"))

        for file_path in python_files:
            # Skip __pycache__ and test files
            if "__pycache__" in str(file_path) or file_path.name.startswith("test_"):
                continue

            self.check_file(file_path)

    def generate_report(self) -> str:
        """Generate a compliance report."""
        report_lines = []

        if self.errors:
            report_lines.append("❌ RLS COMPLIANCE ERRORS:")
            for error in self.errors:
                report_lines.append(f"  • {error}")
            report_lines.append("")

        if self.warnings:
            report_lines.append("⚠️  RLS COMPLIANCE WARNINGS:")
            for warning in self.warnings:
                report_lines.append(f"  • {warning}")
            report_lines.append("")

        report_lines.append("📊 RLS COMPLIANCE SUMMARY:")
        report_lines.append(f"  • UserScopedBase models: {len(self.userscoped_models)}")
        report_lines.append(
            f"  • Models with owner_id: {len(self.models_with_owner_id)}"
        )
        report_lines.append(f"  • Errors: {len(self.errors)}")
        report_lines.append(f"  • Warnings: {len(self.warnings)}")

        if self.userscoped_models:
            report_lines.append(
                f"  • UserScopedBase models: {', '.join(sorted(self.userscoped_models))}"
            )

        return "\n".join(report_lines)

    def is_compliant(self) -> bool:
        """Check if the codebase is RLS compliant."""
        return len(self.errors) == 0


def main():
    """Main entry point for the RLS linter."""
    parser = argparse.ArgumentParser(description="RLS compliance linter")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["app/"],
        help="Paths to check for RLS compliance (default: app/)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first error")

    args = parser.parse_args()

    linter = RLSModelLinter()

    # Check specified paths
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            linter.check_file(path)
        elif path.is_dir():
            linter.check_directory(path)
        else:
            logger.error(f"Path does not exist: {path}")
            sys.exit(1)

    # Generate and display report
    report = linter.generate_report()

    # Use sys.stdout for CLI output
    sys.stdout.write(report)

    if args.verbose:
        sys.stdout.write("\n🔍 DETAILED ANALYSIS:")
        if linter.userscoped_models:
            sys.stdout.write(
                f"\nUserScopedBase models: {sorted(linter.userscoped_models)}"
            )
        if linter.models_with_owner_id:
            sys.stdout.write(
                f"\nModels with owner_id: {sorted(linter.models_with_owner_id)}"
            )

    # Exit with appropriate code
    if not linter.is_compliant():
        logger.error("❌ RLS compliance check failed")
        sys.exit(1)
    else:
        logger.info("✅ RLS compliance check passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
