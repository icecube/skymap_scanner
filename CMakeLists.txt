i3_project(skymap_scanner
  DOCS_DIR resources/docs
  PYTHON_DIR python
  )

# set(LIB_${PROJECT_NAME}_SOURCEFILES
#   private/distribute/I3SkymapScanner.cxx
# )

#set(LIB_${PROJECT_NAME}_SOURCEFILES_PYBINDINGS
#  private/pybindings/module.cxx
#)

# i3_add_library(skymap_scanner
#   ${LIB_${PROJECT_NAME}_SOURCEFILES}
#
#   USE_TOOLS boost python
#
#   USE_PROJECTS icetray dataclasses distribute
# )

# i3_add_pybindings(skymap_scanner
#   ${LIB_${PROJECT_NAME}_SOURCEFILES_PYBINDINGS}
#   USE_TOOLS boost python
#   USE_PROJECTS skymap_scanner icetray dataclasses
# )
# 
# # compile CLASSES_TO_REGISTER and pass it to module.cxx;
# # see module.cxx for details on how this works
# set(CLASSES_TO_REGISTER "")
# foreach(PY_CXX_FILE ${LIB_${PROJECT_NAME}_SOURCEFILES_PYBINDINGS})
#   get_filename_component(BASE_NAME ${PY_CXX_FILE} NAME_WE)
#   if(${BASE_NAME} MATCHES module)
#     set(MODULE_CXX ${PY_CXX_FILE})
#   else()
#     set(CLASSES_TO_REGISTER "${CLASSES_TO_REGISTER}(${BASE_NAME})")
#   endif()
# endforeach()
# set_source_files_properties(${MODULE_CXX}
#   PROPERTIES
#   COMPILE_DEFINITIONS CLASSES_TO_REGISTER=${CLASSES_TO_REGISTER}
# )
# 
# #i3_test_scripts(
# #  resources/test/test_to_be_written.py
# #  )
