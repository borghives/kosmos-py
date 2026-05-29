import kosmos
def main():
    print("Hello from kosmos-py!")
    kosmos.ignite("test.env")
    print(kosmos.ether.UniversalConstants.collapse().project_id)


if __name__ == "__main__":
    main()
