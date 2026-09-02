# 本書の掲載コードを、実務のファイル構成へ分けたものです。
#   make        ビルド
#   make run    ビルドして実行
#   make clean  生成物を消す

CXX      ?= g++
CXXFLAGS ?= -std=c++14 -Wall -I.
TARGET   := app
SRCS     := $(wildcard *.cpp)

$(TARGET): $(SRCS) $(wildcard *.h)
	$(CXX) $(CXXFLAGS) $(SRCS) -o $@

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)

.PHONY: run clean
