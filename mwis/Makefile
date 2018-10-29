CXX = g++ 
CXXFLAGS = -c -O3 -DNDEBUG -std=c++0x -Wall -pipe

SRC_REP = src
SRC = $(wildcard $(SRC_REP)/*.cpp)

OBJ_REP = obj
OBJ = $(addprefix $(OBJ_REP)/,$(notdir $(patsubst %.cpp, %.o, $(SRC))))

print-%  : ; @echo $* = $($*)
DEP := $(OBJ:.o=.d)

#   Targets
mis: $(OBJ) 
	$(CXX) $^ -o bin/mwis

clean:
	rm -rf obj
	rm -f core	
	rm -f bin/mwis

#   General Rules
$(OBJ_REP)/%.o: $(SRC_REP)/%.cpp
	@mkdir -p $(@D)
	$(CXX) $(INCLUDE) $(CXXFLAGS) $< -o $@

-include $(DEP)
