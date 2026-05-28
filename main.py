import kosmos
def main():
    print("Hello from kosmos-py!")
    kosmos.IgniteBase("test.env")
    print(kosmos.ether.UniversalConstants.Collapse().ProjectID)


if __name__ == "__main__":
    main()
