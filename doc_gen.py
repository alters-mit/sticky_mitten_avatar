from pathlib import Path
import re
from typing import List, Dict


class PyDocGen:
    @staticmethod
    def get_doc(filename: str) -> str:
        """
        Create a document from a Python file with the API for each class. Returns the document as a string.

        :param filename: The Python script filename.
        """

        # Create the header.
        doc = "# `" + filename + "`\n\n"

        lines: List[str] = Path(filename).read_text().split("\n")

        for i in range(len(lines)):
            # Create a class description.
            if lines[i].startswith("class"):
                # Skip private classes.
                match = re.search("class _(.*):", lines[i])
                if match is not None:
                    continue
                # Add the name of the class
                class_name = re.search("class (.*):", lines[i]).group(1)
                doc += f"## `{class_name}`\n\n"
                # Add an example.
                class_example = f"`from tdw.{filename[:-3].replace('/', '.')} import " + re.sub(r"(.*)\((.*)\)", r'\1',
                                                                                                class_name) + "`"
                doc += class_example + "\n\n"
                doc += PyDocGen.get_class_description(lines, i)
                # Parse an enum.
                if re.search(r"class (.*)\(Enum\):", lines[i]) is not None:
                    doc += "\n\n" + PyDocGen.get_enum_values(lines, i)
                doc += "\n\n***\n\n"
            # Create a function description.
            elif lines[i].strip().startswith("def"):
                # Skip private functions.
                match = re.search("def _(.*):", lines[i])
                if match is not None and "init" not in match.group(1):
                    continue
                # Append the function description.
                doc += PyDocGen.get_function_documentation(lines, i) + "\n\n***\n\n"

        # Move the "main class" to the top of the document.
        main_class_name = ''.join(x.capitalize() or '_' for x in filename[:-3].split('_'))
        main_class = re.search("(## `" + main_class_name + "`((.|\n)*))", doc)
        if main_class is not None:
            main_class = main_class.group(1)
            doc_header = re.search("(.*)\n\n", doc).group(0)
            doc_temp = doc.replace(main_class, "").replace(doc_header, "")
            doc = doc_header + main_class + doc_temp

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

        # Get the name of the function.
        match = re.search("def (.*):", lines[start_index])
        assert match is not None, f"Bad def:\t{lines[start_index]}"
        func_desc += "#### `" + def_str + "`\n\n"

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
                    continue
                # Get the return description
                elif line.startswith(":return"):
                    return_description = line[8:]
                # Get the overview description of the function.
                else:
                    func_desc += line + "\n"
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

        enum_desc = "Enum values:\n"
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
            enum_desc += "\n- `" + lines[i].strip().split(" = ")[0] + "`"
        return enum_desc

    @staticmethod
    def generate() -> None:
        files = ["sticky_mitten_avatar/avatars/avatar.py",
                 "sticky_mitten_avatar/avatars/baby.py",
                 "sticky_mitten_avatar/dynamic_object_info.py",
                 "sticky_mitten_avatar/static_object_info.py",
                 "sticky_mitten_avatar/sma_controller.py",
                 "sticky_mitten_avatar/frame_data.py",
                 "sticky_mitten_avatar/util.py"]

        output_directory = Path("Documentation")
        if not output_directory.exists():
            output_directory.mkdir()

        # Create documentation for each Python file in the list.
        for python_file in files:
            md_doc = PyDocGen.get_doc(python_file)
            output_filename = python_file.split("/")[-1][:-3] + ".md"
            output_directory.joinpath(output_filename).write_text(md_doc)


if __name__ == "__main__":
    # Test documentation URLs.
    PyDocGen.generate()
