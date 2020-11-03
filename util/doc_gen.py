from json import loads
from pathlib import Path
import re
from typing import List, Dict
from os import chdir


class PyDocGen:
    @staticmethod
    def get_doc(filename: str) -> str:
        """
        Create a document from a Python file with the API for each class. Returns the document as a string.

        :param filename: The Python script filename.
        """

        # Create the header.
        doc = ""

        lines: List[str] = Path(filename).read_text().split("\n")

        api_categories = loads(Path("util/api_categories.json").read_text(encoding="utf-8"))

        class_name = ""
        functions_by_categories = {"": []}

        for i in range(len(lines)):
            # Create a class description.
            if lines[i].startswith("class"):
                # Skip private classes.
                match = re.search("class _(.*):", lines[i])
                if match is not None:
                    continue
                # Add the name of the class
                class_name = re.search("class (.*):", lines[i]).group(1)
                class_header = re.sub(r"(.*)\((.*)\)", r"\1", class_name)

                functions_by_categories.clear()

                doc += f"# {class_header}\n\n"

                import_name = re.sub(r"(.*)\((.*)\)", r'\1', class_name)
                if import_name in ["StickyMittenAvatarController", "Arm"]:
                    class_example = f"`from sticky_mitten_avatar import "
                else:
                    class_example = f"`from sticky_mitten_avatar.{filename[:-3].replace('/', '.')} import "
                class_example += import_name + "`"
                doc += class_example + "\n\n"
                doc += PyDocGen.get_class_description(lines, i)
                # Parse an enum.
                if re.search(r"class (.*)\(Enum\):", lines[i]) is not None:
                    doc += "\n\n" + PyDocGen.get_enum_values(lines, i)
                doc += "\n\n***\n\n"
            # Create a function description.
            elif lines[i].strip().startswith("def"):
                # Skip private functions.
                match = re.search("def _(.*)", lines[i])
                if match is not None and "__init__" not in lines[i]:
                    continue
                # Append the function description.
                function_documentation = PyDocGen.get_function_documentation(lines, i) + "\n\n"
                function_name = re.search("#### (.*)", function_documentation).group(1).replace("\\_", "_")

                # Categorize the functions.
                function_category = ""
                if class_name in api_categories:
                    for category in api_categories[class_name]:
                        if function_name in api_categories[class_name][category]:
                            function_category = category
                            break
                    if function_category == "":
                        print(f"Warning: Uncategorized function {class_name}.{function_name}()")
                if function_category == "":
                    doc += function_documentation
                # Add this later.
                else:
                    if function_category not in functions_by_categories:
                        functions_by_categories[function_category] = list()
                    functions_by_categories[function_category].append(function_documentation)
        if class_name in api_categories:
            for category in api_categories[class_name]:
                if category != "Constructor":
                    doc += f"### {category}\n\n"
                for function in functions_by_categories[category]:
                    doc += function
                doc += "***\n\n"

        return doc

    @staticmethod
    def get_class_description(lines: List[str], start_index: int) -> str:
        """
        Parses a file starting at a line defined by start_index to get the class name and description.
        This assumes that the class has a triple quote description.

        :param lines: All of the lines in the file.
        :param start_index: The start index of the class declaration.
        """

        began_desc = False
        class_desc = ""
        for i in range(start_index, len(lines)):
            if '"""' in lines[i]:
                # Found the terminating triple quote.
                if began_desc:
                    break
                # Found the beginning triple quote.
                else:
                    began_desc = True
                    continue
            elif began_desc:
                if "```" in lines[i]:
                    lines[i] = lines[i].strip()
                else:
                    lines[i] = lines[i][4:]
                class_desc += lines[i] + "\n"
        # Remove trailing new lines.
        while class_desc[-1] == "\n":
            class_desc = class_desc[:-1]
        return class_desc

    @staticmethod
    def get_function_documentation(lines: List[str], start_index: int) -> str:
        began_desc = False
        func_desc = ""

        txt = lines[start_index][:]
        # Get the definition string across multiple lines.
        if "__init__" in lines[start_index]:
            match = re.search(r"def (.*)\):", txt, flags=re.MULTILINE)
            count = 1
            while match is None:
                txt += lines[start_index + count]
                match = re.search(r"def (.*)\):", txt, flags=re.MULTILINE)
                count += 1
            def_str = match.group(1)
            def_str = " ".join(def_str.split()) + ")"
        else:
            match = re.search(r"def (.*) -> (.*):", txt, flags=re.MULTILINE)
            count = 1
            while match is None:
                txt += lines[start_index + count]
                match = re.search(r"def (.*) -> (.*):", txt, flags=re.MULTILINE)
                count += 1
            def_str = match.group(1) + " -> " + match.group(2)
            def_str = " ".join(def_str.split())
        # Used the shortened def string for the header.
        shortened_def_str = def_str.split("(")[0].replace("__", "\\_\\_")

        def_str = def_str.replace("\\ ", "")

        # Get the name of the function.
        match = re.search("def (.*):", lines[start_index])
        assert match is not None, f"Bad def:\t{lines[start_index]}"
        func_desc += "#### " + shortened_def_str + f"\n\n**`def {def_str}`**\n\n"

        is_static = lines[start_index - 1].strip() == "@staticmethod"
        if is_static:
            func_desc += "_This is a static function._\n\n"

        parameters: Dict[str, str] = {}
        return_description = ""
        for i in range(start_index + 1, len(lines)):
            line = lines[i].strip()
            if '"""' in line:
                # Found the terminating triple quote.
                if began_desc:
                    break
                # Found the beginning triple quote.
                else:
                    began_desc = True
                    continue
            elif began_desc:
                # Get a parameter.
                if line.startswith(":param"):
                    param_name = line[7:].split(":")[0]
                    param_desc = line.replace(":param " + param_name + ": ", "").strip()
                    parameters.update({param_name: param_desc})
                elif line == "":
                    func_desc += "\n"
                # Get the return description
                elif line.startswith(":return"):
                    return_description = line[8:]
                # Get the overview description of the function.
                else:
                    func_desc += line + "\n"
        if func_desc[-1] == "\n":
            func_desc = func_desc[:-1]
        # Add the paramter table.
        if len(parameters) > 0:
            func_desc += "\n| Parameter | Description |\n| --- | --- |\n"
            for parameter in parameters:
                func_desc += "| " + parameter + " | " + parameters[parameter] + " |\n"
            func_desc += "\n"
        # Remove trailing new lines.
        while func_desc[-1] == "\n":
            func_desc = func_desc[:-1]
        # Add the return value.
        if return_description != "":
            func_desc += "\n\n_Returns:_ " + return_description
        return func_desc

    @staticmethod
    def get_enum_values(lines: List[str], start_index: int) -> str:
        """
        Returns a list of enum values.

        :param lines: The lines in the document.
        :param start_index: The line of the class defintion.
        """

        enum_desc = "| Value | Description |\n| --- | --- |\n"
        began_class_desc = False
        end_class_desc = False
        for i in range(start_index + 1, len(lines)):
            if "class " in lines[i]:
                break
            if lines[i] == "":
                continue
            if '"""' in lines[i]:
                if not began_class_desc:
                    began_class_desc = True
                else:
                    end_class_desc = True
                continue
            if not end_class_desc:
                continue
            line_split = lines[i].strip().split(" = ")
            val = f"`{line_split[0]}`"
            desc_split = lines[i].strip().split("#")
            if len(desc_split) > 1:
                desc = desc_split[1].strip()
            else:
                desc = ""
            enum_desc += f"| {val} | {desc} |\n"
        return enum_desc.strip()

    @staticmethod
    def generate() -> None:
        files = ["sticky_mitten_avatar/static_object_info.py",
                 "sticky_mitten_avatar/sma_controller.py",
                 "sticky_mitten_avatar/frame_data.py",
                 "sticky_mitten_avatar/body_part_static.py",
                 "sticky_mitten_avatar/task_status.py",
                 "sticky_mitten_avatar/transform.py",
                 "sticky_mitten_avatar/arm.py"]

        output_directory = Path("Documentation")
        if not output_directory.exists():
            output_directory.mkdir()

        # Create documentation for each Python file in the list.
        for python_file in files:
            md_doc = PyDocGen.get_doc(python_file)
            output_filename = python_file.split("/")[-1][:-3] + ".md"
            output_directory.joinpath(output_filename).write_text(md_doc)


if __name__ == "__main__":
    chdir(str(Path("..").resolve()))
    # Test documentation URLs.
    PyDocGen.generate()
