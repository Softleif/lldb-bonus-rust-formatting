use smallvec::SmallVec;
use smol_str::SmolStr;

#[inline(never)]
fn inspect_variables() {
    // Dummy function to set breakpoint on
    std::hint::black_box(());
}

fn main() {
    // Inline variant - small strings (≤23 bytes typically)
    let inline_empty = SmolStr::new("");
    let inline_short = SmolStr::new("hello");
    let inline_medium = SmolStr::new("hello world!");

    // Static variant - using new_static
    const STATIC_STR: &str = "static string";
    let static_str = SmolStr::new_static(STATIC_STR);

    // Heap variant - large strings (>23 bytes)
    let heap_long = SmolStr::new("this is a very long string that will be heap allocated");
    let heap_repeated = SmolStr::new(&"x".repeat(100));

    // Additional test cases
    let inline_inline = SmolStr::new_inline("inline");
    let from_string = SmolStr::from(String::from("from string"));

    // SmallVec variants
    let inline_smallvec: SmallVec<u64, 2> = SmallVec::from([1, 2]);
    let heap_smallvec: SmallVec<u64, 2> = SmallVec::from([1, 2, 4, 5]);
    let empty_smallvec: SmallVec<u32, 4> = SmallVec::new();
    let single_smallvec: SmallVec<i32, 3> = SmallVec::from([42]);

    // Regular Vec for comparison
    let test_vec: Vec<u64> = vec![10, 20, 30];

    // Set breakpoint here - we can inspect all variants
    inspect_variables();
    println!("inline_empty: {}", inline_empty);
    println!("inline_short: {}", inline_short);
    println!("inline_medium: {}", inline_medium);
    println!("static_str: {}", static_str);
    println!("heap_long: {}", heap_long);
    println!("heap_repeated: {}", heap_repeated);
    println!("inline_inline: {}", inline_inline);
    println!("from_string: {}", from_string);
    println!("inline_smallvec: {:?}", inline_smallvec);
    println!("heap_smallvec: {:?}", heap_smallvec);
    println!("empty_smallvec: {:?}", empty_smallvec);
    println!("single_smallvec: {:?}", single_smallvec);
    println!("test_vec: {:?}", test_vec);

    // Keep variables alive for debugging
    let _all = vec![
        inline_empty,
        inline_short,
        inline_medium,
        static_str,
        heap_long,
        heap_repeated,
        inline_inline,
        from_string,
    ];

    let _smallvecs = vec![
        inline_smallvec.len(),
        heap_smallvec.len(),
        empty_smallvec.len(),
        single_smallvec.len(),
        test_vec.len(),
    ];
}
